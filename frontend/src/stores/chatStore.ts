import { create } from "zustand";
import type { Conversation, Message } from "../types/chat";
import { requestMockReply } from "../services/mockChat";

export const LOCAL_CONVERSATION_ID = "local-conversation";

interface ChatState {
  pendingRequest: { id: string; conversationId: string; messageId: string } | null;
  conversations: Omit<Conversation, "messages">[];
  activeConversationId: string;
  draftsByConversation: Record<string, string>;
  messagesByConversation: Record<string, Message[]>;
  createConversation: () => string;
  startNewConversation: () => string;
  deleteConversation: (id: string) => void;
  selectConversation: (id: string) => void;
  setDraft: (id: string, value: string) => void;
  sendMessage: (content: string) => boolean;
  retryMessage: (conversationId: string, messageId: string) => boolean;
  cancelRequest: (reason?: "leave" | "stop") => void;
  stopRequest: () => void;
  resetChat: () => void;
}

let activeController: AbortController | null = null;
let flushActive: (() => void) | null = null;
const initialData = () => {
  const now = new Date().toISOString();
  return {
    pendingRequest: null,
    conversations: [{ id: LOCAL_CONVERSATION_ID, title: "Cuộc trò chuyện mới", created_at: now, updated_at: now }],
    activeConversationId: LOCAL_CONVERSATION_ID,
    draftsByConversation: { [LOCAL_CONVERSATION_ID]: "" },
    messagesByConversation: { [LOCAL_CONVERSATION_ID]: [] as Message[] },
  };
};

async function resolveReply(request: NonNullable<ChatState["pendingRequest"]>, content: string, attempt: number) {
  const controller = new AbortController();
  activeController = controller;
  let received = "";
  let frame: number | null = null;
  const flush = () => {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    if (!received || useChatStore.getState().pendingRequest?.id !== request.id) return;
    useChatStore.setState((state) => ({
      messagesByConversation: {
        ...state.messagesByConversation,
        [request.conversationId]: state.messagesByConversation[request.conversationId].map(
          (message) => message.id === request.messageId ? { ...message, content: received, status: "streaming" } : message,
        ),
      },
    }));
  };
  flushActive = flush;
  const finish = (patch: Partial<Message>) => {
    flush();
    if (useChatStore.getState().pendingRequest?.id !== request.id) return;
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
    const reply = await requestMockReply({ content, attempt, signal: controller.signal, onEvent: (event) => {
      if (controller.signal.aborted || useChatStore.getState().pendingRequest?.id !== request.id) return;
      if (event.type === "delta") {
        received += event.content;
        if (frame === null) frame = requestAnimationFrame(() => { frame = null; flush(); });
      } else {
        flush();
      }
    } });
    finish({ content: reply, status: "done", error: undefined });
  } catch {
    finish({ status: "error", error: "Không thể nhận câu trả lời. Vui lòng thử lại." });
  } finally {
    if (frame !== null) cancelAnimationFrame(frame);
    if (flushActive === flush) flushActive = null;
    if (activeController === controller) activeController = null;
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  ...initialData(),
  stopRequest: () => get().cancelRequest("stop"),
  cancelRequest: (reason = "leave") => {
    const request = get().pendingRequest;
    if (!request) return;
    flushActive?.();
    flushActive = null;
    // Invalidate identity before aborting, so even a late result cannot write back.
    set((state) => ({
      pendingRequest: null,
      messagesByConversation: {
        ...state.messagesByConversation,
        [request.conversationId]: state.messagesByConversation[request.conversationId].map(
          (message) => message.id === request.messageId
            ? { ...message, status: reason === "stop" ? "stopped" : "error", error: reason === "stop" ? undefined : "Yêu cầu đã hủy khi rời cuộc trò chuyện. Bạn có thể thử lại." }
            : message,
        ),
      },
    }));
    activeController?.abort();
    activeController = null;
  },
  resetChat: () => {
    get().cancelRequest();
    set(initialData());
  },
  retryMessage: (conversationId, messageId) => {
    const state = get();
    if (state.pendingRequest) return false;
    const messages = state.messagesByConversation[conversationId];
    const message = messages?.at(-1);
    const user = messages?.at(-2);
    if (!message || message.id !== messageId || message.role !== "assistant" || message.status !== "error" || user?.role !== "user") return false;
    const attempt = (message.attempt ?? 1) + 1;
    const request = { id: crypto.randomUUID(), conversationId, messageId };
    set({
      pendingRequest: request,
      messagesByConversation: {
        ...state.messagesByConversation,
        [conversationId]: messages.map((item) => item.id === messageId
          ? { ...item, content: "", status: "waiting", error: undefined, attempt }
          : item),
      },
    });
    void resolveReply(request, user.content, attempt);
    return true;
  },
  createConversation: () => {
    const state = get();
    if (state.messagesByConversation[state.activeConversationId].length === 0) return state.activeConversationId;
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    set({
      activeConversationId: id,
      conversations: [{ id, title: "Cuộc trò chuyện mới", created_at: now, updated_at: now }, ...state.conversations],
      messagesByConversation: { ...state.messagesByConversation, [id]: [] },
      draftsByConversation: { ...state.draftsByConversation, [id]: "" },
    });
    return id;
  },
  startNewConversation: () => {
    const state = get();
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    set({
      activeConversationId: id,
      conversations: [{ id, title: "Cuộc trò chuyện mới", created_at: now, updated_at: now }, ...state.conversations],
      messagesByConversation: { ...state.messagesByConversation, [id]: [] },
      draftsByConversation: { ...state.draftsByConversation, [id]: "" },
    });
    return id;
  },
  selectConversation: (id) => {
    if (get().conversations.some((conversation) => conversation.id === id)) set({ activeConversationId: id });
  },
  deleteConversation: (id) => {
    if (!get().conversations.some((item) => item.id === id)) return;
    if (get().pendingRequest?.conversationId === id) get().cancelRequest();
    const state = get();
    const conversations = state.conversations.filter((item) => item.id !== id);
    if (conversations.length === 0) {
      set(initialData());
      return;
    }
    const messagesByConversation = { ...state.messagesByConversation };
    const draftsByConversation = { ...state.draftsByConversation };
    delete messagesByConversation[id];
    delete draftsByConversation[id];
    set({
      conversations,
      messagesByConversation,
      draftsByConversation,
      activeConversationId: state.activeConversationId === id ? conversations[0].id : state.activeConversationId,
    });
  },
  setDraft: (id, value) => {
    if (!get().conversations.some((conversation) => conversation.id === id)) return;
    set((state) => ({ draftsByConversation: { ...state.draftsByConversation, [id]: value } }));
  },
  sendMessage: (content) => {
    const trimmed = content.trim();
    if (!trimmed || get().pendingRequest) return false;

    const created_at = new Date().toISOString();
    const messages: Message[] = [
      { id: crypto.randomUUID(), role: "user", content: trimmed, created_at, status: "done" },
      { id: crypto.randomUUID(), role: "assistant", content: "", created_at, status: "waiting", attempt: 1 },
    ];

    const id = get().activeConversationId;
    const request = { id: crypto.randomUUID(), conversationId: id, messageId: messages[1].id };
    set((state) => {
      const conversation = state.conversations.find((item) => item.id === id)!;
      const title = state.messagesByConversation[id].length === 0
        ? Array.from(trimmed.replace(/\s+/g, " ")).slice(0, 40).join("")
        : conversation.title;
      return {
      pendingRequest: request,
      conversations: [
        { ...conversation, title, updated_at: created_at },
        ...state.conversations.filter((item) => item.id !== id),
      ],
      draftsByConversation: { ...state.draftsByConversation, [id]: "" },
      messagesByConversation: {
        ...state.messagesByConversation,
        [id]: [
          ...state.messagesByConversation[id],
          ...messages,
        ],
      },
    }; });
    void resolveReply(request, trimmed, 1);
    return true;
  },
}));
