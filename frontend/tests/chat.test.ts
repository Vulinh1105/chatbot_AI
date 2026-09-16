import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatStore } from "../src/stores/chatStore";
import * as api from "../src/services/chatService";

vi.mock("../src/services/chatService", () => ({
  createChat: vi.fn(), getChats: vi.fn(), getMessages: vi.fn(), askQuestion: vi.fn(), deleteChat: vi.fn(),
}));

const state = () => useChatStore.getState();
const messages = (id = state().activeConversationId) => state().messagesByConversation[id];
const chat = (id: number): api.ApiChat => ({ id, owner_id: 2, title: `Chat ${id}`, created_at: "2026-09-15", updated_at: "2026-09-15" });
const reply = (id = 2, chatId = 7): api.ApiMessage => ({
  id, chat_id: chatId, role: "system", content: "Câu trả lời thật", status: "completed",
  sources: [{ source: "policy.pdf", pages: [2, 3] }], created_at: "2026-09-15",
});
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const flush = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };

beforeEach(() => {
  state().resetChat();
  vi.resetAllMocks();
  vi.mocked(api.createChat).mockResolvedValue(chat(7));
  vi.mocked(api.askQuestion).mockResolvedValue(reply());
  vi.mocked(api.getChats).mockResolvedValue({ items: [chat(7)], has_more: false, next_cursor: null });
  vi.mocked(api.getMessages).mockResolvedValue({ chat: chat(7), messages: [reply()], has_more: false, next_cursor: null });
  vi.mocked(api.deleteChat).mockResolvedValue(undefined);
});

describe("chat API lifecycle", () => {
  it("creates a backend chat before asking, maps response and keeps sources", async () => {
    expect(state().sendMessage("   ")).toBe(false);
    expect(state().sendMessage("x".repeat(5001))).toBe(false);
    expect(state().sendMessage(" hello ")).toBe(true);
    expect(messages()[0].content).toBe("hello");
    expect(messages()[1].status).toBe("waiting");
    expect(state().sendMessage("duplicate")).toBe(false);
    await flush();
    expect(api.createChat).toHaveBeenCalledWith("hello");
    expect(api.askQuestion).toHaveBeenCalledWith("7", "hello", expect.any(AbortSignal));
    expect(messages()[1]).toMatchObject({ id: "2", role: "assistant", status: "done", sources: reply().sources });
    vi.mocked(api.askQuestion).mockResolvedValueOnce(reply(4));
    state().sendMessage("next");
    await flush();
    expect(api.createChat).toHaveBeenCalledTimes(1);
    expect(messages()).toHaveLength(4);
  });

  it("reuses an in-flight creation after cancellation without sending the old question", async () => {
    const creation = deferred<api.ApiChat>();
    vi.mocked(api.createChat).mockReturnValueOnce(creation.promise);
    state().sendMessage("old");
    state().stopRequest();
    expect(messages()[1].status).toBe("stopped");
    state().sendMessage("new");
    creation.resolve(chat(7));
    await flush();
    expect(api.createChat).toHaveBeenCalledTimes(1);
    expect(api.askQuestion).toHaveBeenCalledTimes(1);
    expect(api.askQuestion).toHaveBeenCalledWith("7", "new", expect.any(AbortSignal));
    expect(messages()[1].status).toBe("stopped");
    expect(messages()[3].status).toBe("done");
  });

  it("ignores a late answer after stop and keeps a newer request locked", async () => {
    const old = deferred<api.ApiMessage>();
    const next = deferred<api.ApiMessage>();
    vi.mocked(api.askQuestion).mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
    state().sendMessage("old"); await flush();
    const signal = vi.mocked(api.askQuestion).mock.calls[0][2];
    state().stopRequest();
    expect(signal?.aborted).toBe(true);
    state().sendMessage("new"); await flush();
    const pending = state().pendingRequest;
    old.resolve(reply()); await flush();
    expect(state().pendingRequest).toBe(pending);
    expect(messages()[1].status).toBe("stopped");
    next.resolve(reply(4)); await flush();
    expect(messages()[3].id).toBe("4");
  });

  it("keeps replies in their original chat while another draft is edited", async () => {
    const late = deferred<api.ApiMessage>();
    vi.mocked(api.askQuestion).mockReturnValueOnce(late.promise);
    const original = state().activeConversationId;
    state().sendMessage("A"); await flush();
    const other = state().startNewConversation();
    state().setDraft(other, "draft B");
    late.resolve(reply()); await flush();
    expect(messages(original)[1].status).toBe("done");
    expect(messages(other)).toEqual([]);
    expect(state().draftsByConversation[other]).toBe("draft B");
  });

  it("supports retry after failure without duplicating the optimistic user message", async () => {
    vi.mocked(api.askQuestion).mockRejectedValueOnce(new Error("offline"));
    state().sendMessage("hello"); await flush();
    const id = state().activeConversationId;
    const failed = messages()[1].id;
    expect(messages()[1].status).toBe("error");
    expect(state().retryMessage(id, failed)).toBe(true);
    expect(state().retryMessage(id, failed)).toBe(false);
    await flush();
    expect(messages()).toHaveLength(2);
    expect(messages()[1].status).toBe("done");
    expect(api.createChat).toHaveBeenCalledTimes(1);
  });

  it("loads every list/history page and uses backend IDs for existing chats", async () => {
    vi.mocked(api.getChats)
      .mockResolvedValueOnce({ items: [chat(7)], has_more: true, next_cursor: 7 })
      .mockResolvedValueOnce({ items: [chat(6)], has_more: false, next_cursor: null });
    await state().loadConversations();
    expect(api.getChats).toHaveBeenNthCalledWith(2, 7);
    const user: api.ApiMessage = { ...reply(1), role: "user", content: "Question" };
    vi.mocked(api.getMessages)
      .mockResolvedValueOnce({ chat: chat(7), messages: [user], has_more: true, next_cursor: 1 })
      .mockResolvedValueOnce({ chat: chat(7), messages: [reply()], has_more: false, next_cursor: null });
    state().selectConversation("7");
    expect(state().sendMessage("blocked while loading")).toBe(false);
    await flush();
    expect(api.getMessages).toHaveBeenNthCalledWith(2, "7", 1);
    expect(messages().map((message) => message.role)).toEqual(["user", "assistant"]);
    state().sendMessage("follow up"); await flush();
    expect(api.createChat).not.toHaveBeenCalled();
  });

  it("does not overwrite a different active conversation with delayed history", async () => {
    await state().loadConversations();
    const late = deferred<api.ChatHistoryResponse>();
    vi.mocked(api.getMessages).mockReturnValueOnce(late.promise);
    state().selectConversation("7");
    const other = state().startNewConversation();
    late.resolve({ chat: chat(7), messages: [reply()], has_more: false, next_cursor: null });
    await flush();
    expect(state().activeConversationId).toBe(other);
    expect(messages()).toEqual([]);
    expect(messages("7")[0].content).toBe(reply().content);
  });

  it("keeps conversation on failed delete, then removes it after successful delete", async () => {
    await state().loadConversations();
    vi.mocked(api.deleteChat).mockRejectedValueOnce(new Error("offline"));
    await state().deleteConversation("7");
    expect(state().conversations.some((item) => item.id === "7")).toBe(true);
    expect(state().error).toBeTruthy();
    await state().deleteConversation("7");
    expect(api.deleteChat).toHaveBeenCalledWith("7");
    expect(state().conversations.some((item) => item.id === "7")).toBe(false);
  });

  it("waits for creation before deleting an in-flight new chat", async () => {
    const late = deferred<api.ApiChat>();
    vi.mocked(api.createChat).mockReturnValueOnce(late.promise);
    const id = state().activeConversationId;
    state().sendMessage("hello");
    const deletion = state().deleteConversation(id);
    late.resolve(chat(7)); await deletion; await flush();
    expect(api.askQuestion).not.toHaveBeenCalled();
    expect(api.deleteChat).toHaveBeenCalledWith("7");
    expect(messages()).toEqual([]);
  });

  it("discards list, history and create responses from a previous login session", async () => {
    const list = deferred<api.ChatListResponse>();
    vi.mocked(api.getChats).mockReturnValueOnce(list.promise);
    const loading = state().loadConversations();
    state().resetChat();
    list.resolve({ items: [chat(99)], has_more: false, next_cursor: null }); await loading;
    expect(state().serverIds).toEqual({});
    const creation = deferred<api.ApiChat>();
    vi.mocked(api.createChat).mockReturnValueOnce(creation.promise);
    state().sendMessage("private"); state().resetChat();
    creation.resolve(chat(99)); await flush();
    expect(api.askQuestion).not.toHaveBeenCalled();
    expect(state().serverIds).toEqual({});
    await state().loadConversations();
    const history = deferred<api.ChatHistoryResponse>();
    vi.mocked(api.getMessages).mockReturnValueOnce(history.promise);
    state().selectConversation("7"); state().resetChat();
    history.resolve({ chat: chat(7), messages: [reply()], has_more: false, next_cursor: null });
    await flush();
    expect(messages()).toEqual([]);
    expect(state().messagesByConversation["7"]).toBeUndefined();
  });

  it("shows history failure and allows a successful reload", async () => {
    await state().loadConversations();
    vi.mocked(api.getMessages).mockRejectedValueOnce(new Error("offline"));
    state().selectConversation("7"); await flush();
    expect(state().historyErrors["7"]).toBeTruthy();
    expect(state().sendMessage("blocked")).toBe(false);
    await state().loadHistory("7");
    expect(state().historyErrors["7"]).toBe("");
    expect(messages()).toHaveLength(1);
  });
});
