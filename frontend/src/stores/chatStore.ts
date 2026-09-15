import { create } from "zustand";
import axios from "axios";
import type { Conversation, Message } from "../types/chat";
import * as api from "../services/chatService";

export const LOCAL_CONVERSATION_ID = "local-conversation";
type Pending = { id: string; conversationId: string; messageId: string };

interface ChatState {
  pendingRequest: Pending | null;
  conversations: Omit<Conversation, "messages">[];
  activeConversationId: string;
  draftsByConversation: Record<string, string>;
  messagesByConversation: Record<string, Message[]>;
  serverIds: Record<string, string>;
  loadingHistory: Record<string, boolean>;
  loadedHistory: Record<string, boolean>;
  historyErrors: Record<string, string>;
  deleting: Record<string, boolean>;
  loadingConversations: boolean;
  initialized: boolean;
  error: string | null;
  loadConversations: () => Promise<void>;
  loadHistory: (id: string) => Promise<void>;
  createConversation: () => string;
  startNewConversation: () => string;
  deleteConversation: (id: string) => Promise<void>;
  selectConversation: (id: string) => void;
  setDraft: (id: string, value: string) => void;
  sendMessage: (content: string) => boolean;
  retryMessage: (conversationId: string, messageId: string) => boolean;
  cancelRequest: (reason?: "leave" | "stop") => void;
  stopRequest: () => void;
  resetChat: () => void;
}

let epoch = 0;
let listGeneration = 0;
let activeController: AbortController | null = null;
const creating = new Map<string, Promise<string>>();

const initialData = () => {
  const now = new Date().toISOString();
  return {
    pendingRequest: null,
    conversations: [{ id: LOCAL_CONVERSATION_ID, title: "Cuộc trò chuyện mới", created_at: now, updated_at: now }],
    activeConversationId: LOCAL_CONVERSATION_ID,
    draftsByConversation: { [LOCAL_CONVERSATION_ID]: "" },
    messagesByConversation: { [LOCAL_CONVERSATION_ID]: [] as Message[] },
    serverIds: {} as Record<string, string>,
    loadingHistory: {} as Record<string, boolean>,
    loadedHistory: {} as Record<string, boolean>,
    historyErrors: {} as Record<string, string>,
    deleting: {} as Record<string, boolean>,
    loadingConversations: false,
    initialized: false,
    error: null,
  };
};

export function toMessage(item: api.ApiMessage): Message {
  return {
    id: String(item.id), role: item.role === "system" ? "assistant" : "user",
    content: item.content, created_at: item.created_at, sources: item.sources,
    status: item.status === "completed" ? "done" : item.status === "pending" ? "waiting" : "error",
  };
}

function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 401) return "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.";
    if (error.response?.status === 503) return "Dịch vụ trả lời đang không khả dụng. Vui lòng thử lại sau.";
    if (error.response?.status === 404) return "Không tìm thấy hội thoại hoặc API chat chưa được triển khai.";
    if (error.code === "ECONNABORTED") return "Chờ phản hồi quá lâu. Hãy tải lại lịch sử trước khi gửi lại để tránh trùng câu hỏi.";
  }
  return "Không thể kết nối hoặc xử lý yêu cầu. Nếu vừa gửi câu hỏi, hãy tải lại lịch sử trước khi thử lại.";
}

// Keep local UI keys stable while using only backend IDs in HTTP requests.
async function ensureServerChat(id: string): Promise<string> {
  const state = useChatStore.getState();
  if (state.serverIds[id]) return state.serverIds[id];
  const existing = creating.get(id);
  if (existing) return existing;
  const version = epoch;
  const title = state.conversations.find((chat) => chat.id === id)?.title ?? "Cuộc trò chuyện mới";
  const operation = api.createChat(title).then((chat) => {
    if (epoch !== version) throw new Error("Session changed");
    useChatStore.setState((current) => ({ serverIds: { ...current.serverIds, [id]: String(chat.id) } }));
    return String(chat.id);
  });
  creating.set(id, operation);
  try { return await operation; }
  finally { if (creating.get(id) === operation) creating.delete(id); }
}

async function resolveReply(request: Pending, content: string) {
  const controller = new AbortController();
  activeController = controller;
  const current = () => useChatStore.getState().pendingRequest?.id === request.id;
  const finish = (patch: Partial<Message>) => {
    if (!current()) return;
    useChatStore.setState((state) => ({
      pendingRequest: null,
      messagesByConversation: {
        ...state.messagesByConversation,
        [request.conversationId]: state.messagesByConversation[request.conversationId].map(
          (message) => message.id === request.messageId ? { ...message, ...patch } : message,
        ),
      },
    }));
  };
  try {
    const serverId = await ensureServerChat(request.conversationId);
    if (!current()) return;
    const reply = await api.askQuestion(serverId, content, controller.signal);
    finish({ ...toMessage(reply), error: undefined });
  } catch (error) {
    finish({ status: "error", error: errorText(error) });
  } finally {
    if (activeController === controller) activeController = null;
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  ...initialData(),
  loadConversations: async () => {
    if (get().loadingConversations) return;
    const version = epoch;
    const generation = ++listGeneration;
    set({ loadingConversations: true, error: null });
    try {
      const chats: api.ApiChat[] = [];
      let cursor: number | undefined;
      const seen = new Set<number>();
      do {
        const page = await api.getChats(cursor);
        if (version !== epoch || generation !== listGeneration) return;
        chats.push(...page.items);
        if (!page.has_more) break;
        if (page.next_cursor === null || seen.has(page.next_cursor)) throw new Error("Invalid cursor");
        seen.add(page.next_cursor);
        cursor = page.next_cursor;
      } while (cursor !== undefined);
      set((state) => {
        const conversations = [...state.conversations];
        const serverIds = { ...state.serverIds };
        const messagesByConversation = { ...state.messagesByConversation };
        const draftsByConversation = { ...state.draftsByConversation };
        for (const chat of chats) {
          const serverId = String(chat.id);
          if (Object.values(serverIds).includes(serverId) || state.deleting[serverId]) continue;
          conversations.push({ ...chat, id: serverId });
          serverIds[serverId] = serverId;
          messagesByConversation[serverId] = [];
          draftsByConversation[serverId] = "";
        }
        return { conversations, serverIds, messagesByConversation, draftsByConversation, initialized: true };
      });
    } catch (error) { if (version === epoch && generation === listGeneration) set({ error: errorText(error) }); }
    finally { if (version === epoch && generation === listGeneration) set({ loadingConversations: false }); }
  },
  loadHistory: async (id) => {
    const state = get();
    const serverId = state.serverIds[id];
    if (!serverId || state.loadingHistory[id] || state.deleting[id] || state.pendingRequest?.conversationId === id) return;
    const version = epoch;
    set({ loadingHistory: { ...state.loadingHistory, [id]: true }, historyErrors: { ...state.historyErrors, [id]: "" } });
    try {
      const messages: Message[] = [];
      let cursor: number | undefined;
      const seen = new Set<number>();
      do {
        const page = await api.getMessages(serverId, cursor);
        if (epoch !== version || !get().conversations.some((chat) => chat.id === id) || get().deleting[id]) return;
        messages.push(...page.messages.map(toMessage));
        if (!page.has_more) break;
        if (page.next_cursor === null || seen.has(page.next_cursor)) throw new Error("Invalid cursor");
        seen.add(page.next_cursor);
        cursor = page.next_cursor;
      } while (cursor !== undefined);
      set((current) => ({
        messagesByConversation: { ...current.messagesByConversation, [id]: [...new Map(messages.map((message) => [message.id, message])).values()] },
        loadedHistory: { ...current.loadedHistory, [id]: true },
      }));
    } catch (error) {
      if (version === epoch && get().conversations.some((chat) => chat.id === id)) set((current) => ({ historyErrors: { ...current.historyErrors, [id]: errorText(error) } }));
    } finally {
      if (version === epoch) set((current) => ({ loadingHistory: { ...current.loadingHistory, [id]: false } }));
    }
  },
  stopRequest: () => get().cancelRequest("stop"),
  cancelRequest: (reason = "leave") => {
    const request = get().pendingRequest;
    if (!request) return;
    set((state) => ({
      pendingRequest: null,
      messagesByConversation: {
        ...state.messagesByConversation,
        [request.conversationId]: state.messagesByConversation[request.conversationId].map((message) =>
          message.id === request.messageId ? { ...message, status: reason === "stop" ? "stopped" : "error",
            error: "Đã hủy chờ. Máy chủ có thể vẫn xử lý; hãy tải lại lịch sử trước khi gửi lại." } : message),
      },
    }));
    activeController?.abort();
    activeController = null;
  },
  resetChat: () => {
    get().cancelRequest();
    epoch += 1;
    creating.clear();
    listGeneration += 1;
    set(initialData());
  },
  retryMessage: (conversationId, messageId) => {
    const state = get();
    if (state.pendingRequest || state.loadingHistory[conversationId] || state.deleting[conversationId]) return false;
    const messages = state.messagesByConversation[conversationId];
    const message = messages?.at(-1);
    const user = messages?.at(-2);
    if (!message || message.id !== messageId || message.role !== "assistant" || message.status !== "error" || user?.role !== "user") return false;
    const request = { id: crypto.randomUUID(), conversationId, messageId };
    set({ pendingRequest: request, messagesByConversation: {
      ...state.messagesByConversation,
      [conversationId]: messages.map((item) => item.id === messageId ? { ...item, content: "", status: "waiting", error: undefined } : item),
    } });
    void resolveReply(request, user.content);
    return true;
  },
  createConversation: () => {
    const state = get();
    if (!state.serverIds[state.activeConversationId] && state.messagesByConversation[state.activeConversationId]?.length === 0) return state.activeConversationId;
    return get().startNewConversation();
  },
  startNewConversation: () => {
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    set((state) => ({
      activeConversationId: id,
      conversations: [{ id, title: "Cuộc trò chuyện mới", created_at: now, updated_at: now }, ...state.conversations],
      messagesByConversation: { ...state.messagesByConversation, [id]: [] },
      draftsByConversation: { ...state.draftsByConversation, [id]: "" },
    }));
    return id;
  },
  selectConversation: (id) => {
    if (!get().conversations.some((chat) => chat.id === id) || get().deleting[id]) return;
    set({ activeConversationId: id });
    if (!get().loadedHistory[id] && get().messagesByConversation[id].length === 0) void get().loadHistory(id);
  },
  deleteConversation: async (id) => {
    if (!get().conversations.some((chat) => chat.id === id) || get().deleting[id]) return;
    if (get().pendingRequest?.conversationId === id) get().cancelRequest();
    const version = epoch;
    listGeneration += 1;
    set((state) => ({ deleting: { ...state.deleting, [id]: true }, loadingConversations: false, error: null }));
    try {
      const serverId = get().serverIds[id] ?? await creating.get(id);
      if (version !== epoch) return;
      if (serverId) await api.deleteChat(serverId);
      if (version !== epoch) return;
      set((state) => {
        const conversations = state.conversations.filter((chat) => chat.id !== id);
        const messagesByConversation = { ...state.messagesByConversation };
        const draftsByConversation = { ...state.draftsByConversation };
        const serverIds = { ...state.serverIds };
        delete messagesByConversation[id]; delete draftsByConversation[id]; delete serverIds[id];
        if (!conversations.length) {
          const fresh = initialData();
          return { conversations: fresh.conversations, activeConversationId: fresh.activeConversationId,
            messagesByConversation: fresh.messagesByConversation, draftsByConversation: fresh.draftsByConversation, serverIds };
        }
        return { conversations, messagesByConversation, draftsByConversation, serverIds,
          activeConversationId: state.activeConversationId === id ? conversations[0].id : state.activeConversationId };
      });
      set((state) => {
        const loadedHistory = { ...state.loadedHistory };
        const historyErrors = { ...state.historyErrors };
        delete loadedHistory[id]; delete historyErrors[id];
        return { loadedHistory, historyErrors };
      });
      get().selectConversation(get().activeConversationId);
    } catch (error) { if (version === epoch) set({ error: errorText(error) }); }
    finally { if (version === epoch) set((state) => ({ deleting: { ...state.deleting, [id]: false } })); }
  },
  setDraft: (id, value) => {
    if (get().conversations.some((chat) => chat.id === id)) set((state) => ({ draftsByConversation: { ...state.draftsByConversation, [id]: value } }));
  },
  sendMessage: (content) => {
    const trimmed = content.trim();
    const state = get();
    const id = state.activeConversationId;
    if (!trimmed || trimmed.length > 5000 || state.pendingRequest || state.loadingHistory[id] || state.historyErrors[id] || state.deleting[id]) return false;
    const now = new Date().toISOString();
    const messages: Message[] = [
      { id: crypto.randomUUID(), role: "user", content: trimmed, created_at: now, status: "done" },
      { id: crypto.randomUUID(), role: "assistant", content: "", created_at: now, status: "waiting" },
    ];
    const request = { id: crypto.randomUUID(), conversationId: id, messageId: messages[1].id };
    const conversation = state.conversations.find((chat) => chat.id === id)!;
    const title = !state.serverIds[id] && !state.messagesByConversation[id].length
      ? Array.from(trimmed.replace(/\s+/g, " ")).slice(0, 40).join("") : conversation.title;
    set({
      pendingRequest: request,
      conversations: [{ ...conversation, title, updated_at: now }, ...state.conversations.filter((chat) => chat.id !== id)],
      draftsByConversation: { ...state.draftsByConversation, [id]: "" },
      messagesByConversation: { ...state.messagesByConversation, [id]: [...state.messagesByConversation[id], ...messages] },
    });
    void resolveReply(request, trimmed);
    return true;
  },
}));
