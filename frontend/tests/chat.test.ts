import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useChatStore } from "../src/stores/chatStore";
import * as service from "../src/services/mockChat";

const state = () => useChatStore.getState();
const messages = (id = state().activeConversationId) => state().messagesByConversation[id];

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => setTimeout(() => callback(0), 16));
  vi.stubGlobal("cancelAnimationFrame", (id: ReturnType<typeof setTimeout>) => clearTimeout(id));
  state().resetChat();
});
afterEach(() => {
  state().resetChat();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("chat request lifecycle", () => {
  it("streams into one assistant message and flushes complete content", async () => {
    state().sendMessage("hello");
    const id = messages()[1].id;
    await vi.advanceTimersByTimeAsync(1216);
    expect(messages()[1]).toMatchObject({ id, status: "streaming" });
    const first = messages()[1].content;
    expect(first.length).toBeGreaterThan(0);
    await vi.advanceTimersByTimeAsync(160);
    expect(messages()[1].content.length).toBeGreaterThan(first.length);
    expect(messages()).toHaveLength(2);
    await vi.runAllTimersAsync();
    expect(messages()[1]).toMatchObject({ id, status: "done" });
    expect(messages()[1].content.endsWith("```" )).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("stops before first chunk and immediately permits a new send", async () => {
    state().sendMessage("[slow]");
    state().stopRequest();
    expect(messages()[1]).toMatchObject({ content: "", status: "stopped" });
    expect(state().pendingRequest).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
    expect(state().sendMessage("next")).toBe(true);
    await vi.runAllTimersAsync();
    expect(messages()[1].status).toBe("stopped");
    expect(messages()[3].status).toBe("done");
  });

  it("flushes buffered content when stopped between frames and ignores late events", async () => {
    let emit!: service.MockChatRequest["onEvent"];
    let finish!: (value: string) => void;
    vi.spyOn(service, "requestMockReply").mockImplementationOnce((request) => {
      emit = request.onEvent;
      return new Promise((resolve) => { finish = resolve; });
    });
    state().sendMessage("stop");
    emit({ type: "delta", content: "partial" });
    expect(messages()[1].content).toBe("");
    state().stopRequest();
    expect(messages()[1]).toMatchObject({ content: "partial", status: "stopped" });
    expect(vi.getTimerCount()).toBe(0);
    state().sendMessage("new");
    emit({ type: "delta", content: "STALE" });
    emit({ type: "done" });
    finish("STALE");
    await vi.runAllTimersAsync();
    expect(messages()[1]).toMatchObject({ content: "partial", status: "stopped" });
    expect(messages()[3].status).toBe("done");
  });

  it("retains partial text on stream error and replaces it on retry", async () => {
    const id = state().activeConversationId;
    state().sendMessage("[stream-error]");
    await vi.runAllTimersAsync();
    const reply = messages()[1];
    expect(reply.status).toBe("error");
    expect(reply.content.length).toBeGreaterThan(0);
    expect(state().retryMessage(id, reply.id)).toBe(true);
    expect(messages()[1].content).toBe("");
    await vi.runAllTimersAsync();
    expect(messages()).toHaveLength(2);
    expect(messages()[1]).toMatchObject({ id: reply.id, status: "done" });
    expect(messages()[1].content.startsWith(reply.content)).toBe(true);
  });

  it("batches rapid deltas into one update per frame", async () => {
    let emit!: service.MockChatRequest["onEvent"];
    let finish!: (value: string) => void;
    vi.spyOn(service, "requestMockReply").mockImplementationOnce((request) => {
      emit = request.onEvent;
      return new Promise((resolve) => { finish = resolve; });
    });
    state().sendMessage("fast");
    const listener = vi.fn();
    const unsubscribe = useChatStore.subscribe(listener);
    emit({ type: "delta", content: "a" });
    emit({ type: "delta", content: "b" });
    emit({ type: "delta", content: "c" });
    expect(listener).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(16);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(messages()[1].content).toBe("abc");
    emit({ type: "delta", content: "d" });
    emit({ type: "done" });
    finish("abcd");
    await Promise.resolve();
    expect(messages()[1]).toMatchObject({ content: "abcd", status: "done" });
    expect(vi.getTimerCount()).toBe(0);
    unsubscribe();
  });

  it("keeps partial content on route cleanup and discards queued frames on deletion", async () => {
    state().sendMessage("[fast]");
    await vi.advanceTimersByTimeAsync(1201);
    state().cancelRequest();
    expect(messages()[1].content.length).toBeGreaterThan(0);
    expect(messages()[1].status).toBe("error");
    expect(vi.getTimerCount()).toBe(0);
    state().sendMessage("[fast]");
    await vi.advanceTimersByTimeAsync(1201);
    state().deleteConversation(state().activeConversationId);
    await vi.runAllTimersAsync();
    expect(messages()).toEqual([]);
    expect(vi.getTimerCount()).toBe(0);
  });
  it("deletes inactive history/draft without affecting active conversation", async () => {
    const a = state().activeConversationId;
    state().sendMessage("A");
    await vi.advanceTimersByTimeAsync(3000);
    state().setDraft(a, "draft A");
    const b = state().createConversation();
    state().setDraft(b, "draft B");
    state().deleteConversation(a);
    expect(state().activeConversationId).toBe(b);
    expect(state().messagesByConversation[a]).toBeUndefined();
    expect(state().draftsByConversation[a]).toBeUndefined();
    expect(state().draftsByConversation[b]).toBe("draft B");
    state().deleteConversation("missing");
    expect(state().conversations).toHaveLength(1);
    state().deleteConversation(b);
    expect(state().conversations).toHaveLength(1);
    expect(messages()).toEqual([]);
    expect(Object.values(state().draftsByConversation)).toEqual([""]);
  });

  it("starts a genuinely new empty conversation from the new-chat action", () => {
    const oldId = state().activeConversationId;
    state().sendMessage("old conversation");
    const newId = state().startNewConversation();
    expect(newId).not.toBe(oldId);
    expect(state().activeConversationId).toBe(newId);
    expect(state().messagesByConversation[newId]).toEqual([]);
    expect(state().draftsByConversation[newId]).toBe("");
    expect(state().messagesByConversation[oldId]).toHaveLength(2);
    expect(state().conversations[0].id).toBe(newId);
    expect(state().conversations.some((item) => item.id === oldId)).toBe(true);
  });

  it("deletes an active pending conversation, selects remaining and ignores late reply", async () => {
    state().sendMessage("A");
    await vi.advanceTimersByTimeAsync(3000);
    const a = state().activeConversationId;
    const b = state().createConversation();
    let resolveLate!: (value: string) => void;
    let signal!: AbortSignal;
    vi.spyOn(service, "requestMockReply").mockImplementationOnce((request) => {
      signal = request.signal;
      return new Promise((resolve) => { resolveLate = resolve; });
    });
    state().sendMessage("B");
    state().deleteConversation(b);
    expect(signal.aborted).toBe(true);
    expect(state().activeConversationId).toBe(a);
    expect(state().pendingRequest).toBeNull();
    resolveLate("late B");
    await Promise.resolve();
    expect(state().messagesByConversation[b]).toBeUndefined();
    expect(messages(a)).toHaveLength(2);
  });

  it("does not cancel a different conversation's pending reply when deleting", async () => {
    const a = state().activeConversationId;
    state().sendMessage("[slow]");
    const b = state().createConversation();
    const pending = state().pendingRequest;
    state().deleteConversation(b);
    expect(state().pendingRequest).toBe(pending);
    await vi.advanceTimersByTimeAsync(7000);
    expect(messages(a)[1].status).toBe("done");
  });
  it("shows user immediately, rejects empty/duplicate sends and unlocks after success", async () => {
    expect(state().sendMessage("  ")).toBe(false);
    expect(state().sendMessage(" hello ")).toBe(true);
    expect(messages().map((m) => [m.role, m.status])).toEqual([["user", "done"], ["assistant", "waiting"]]);
    expect(messages()[0].content).toBe("hello");
    expect(state().sendMessage("duplicate")).toBe(false);
    expect(messages()).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(3000);
    expect(messages()[1].status).toBe("done");
    expect(messages()[1].content).toContain("**");
    expect(state().pendingRequest).toBeNull();
  });

  it("keeps replies in the original conversation and preserves another draft", async () => {
    const a = state().activeConversationId;
    state().sendMessage("[slow]");
    const b = state().createConversation();
    state().setDraft(b, "draft B");
    expect(state().sendMessage("blocked B")).toBe(false);
    await vi.advanceTimersByTimeAsync(3000);
    expect(messages(a)[1].status).toBe("waiting");
    await vi.advanceTimersByTimeAsync(4000);
    expect(messages(a)[1].status).toBe("done");
    expect(messages(b)).toEqual([]);
    expect(state().draftsByConversation[b]).toBe("draft B");
    expect(state().activeConversationId).toBe(b);
  });

  it("retries the same failed reply without duplicating user and rejects duplicate retry", async () => {
    const id = state().activeConversationId;
    state().sendMessage("[error]");
    await vi.advanceTimersByTimeAsync(3000);
    const [user, reply] = messages();
    expect(reply.status).toBe("error");
    expect(state().retryMessage(id, reply.id)).toBe(true);
    expect(state().retryMessage(id, reply.id)).toBe(false);
    expect(messages()).toHaveLength(2);
    expect(messages()[0]).toBe(user);
    await vi.advanceTimersByTimeAsync(3000);
    expect(messages()[1]).toMatchObject({ id: reply.id, status: "done", attempt: 2 });
    expect(state().retryMessage(id, reply.id)).toBe(false);
  });

  it("rejects old failed replies and unknown IDs", async () => {
    const id = state().activeConversationId;
    state().sendMessage("[error]");
    await vi.advanceTimersByTimeAsync(3000);
    const old = messages()[1].id;
    state().sendMessage("new turn");
    await vi.advanceTimersByTimeAsync(3000);
    expect(state().retryMessage(id, old)).toBe(false);
    expect(state().retryMessage("missing", old)).toBe(false);
    expect(state().retryMessage(id, "missing")).toBe(false);
  });

  it("cancels on session cleanup, clears timer and allows retry on return", async () => {
    const id = state().activeConversationId;
    state().sendMessage("[slow]");
    const replyId = messages()[1].id;
    state().cancelRequest();
    expect(state().pendingRequest).toBeNull();
    expect(messages()[1].status).toBe("error");
    expect(vi.getTimerCount()).toBe(0);
    await vi.runAllTimersAsync();
    expect(messages()[1].status).toBe("error");
    expect(state().retryMessage(id, replyId)).toBe(true);
    await vi.advanceTimersByTimeAsync(7000);
    expect(messages()[1].status).toBe("done");
  });

  it("ignores late success after cancel without unlocking a newer request", async () => {
    let resolveLate!: (value: string) => void;
    vi.spyOn(service, "requestMockReply").mockImplementationOnce(() => new Promise((resolve) => { resolveLate = resolve; }));
    state().sendMessage("old");
    state().cancelRequest();
    state().sendMessage("new");
    const pending = state().pendingRequest;
    resolveLate("STALE");
    await Promise.resolve();
    expect(state().pendingRequest).toBe(pending);
    expect(messages()[1].status).toBe("error");
    expect(messages()[1].content).not.toBe("STALE");
    await vi.advanceTimersByTimeAsync(3000);
    expect(messages()[3].status).toBe("done");
  });

  it("logout clears history/drafts, aborts request and ignores late rejection", async () => {
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => null), setItem: vi.fn(), removeItem: vi.fn() });
    const { useAuthStore } = await import("../src/stores/authStore");
    let rejectLate!: (error: Error) => void;
    let signal!: AbortSignal;
    vi.spyOn(service, "requestMockReply").mockImplementationOnce((request) => {
      signal = request.signal;
      return new Promise((_resolve, reject) => { rejectLate = reject; });
    });
    state().sendMessage("old session");
    const b = state().createConversation();
    state().setDraft(b, "private draft");
    useAuthStore.getState().logout();
    expect(signal.aborted).toBe(true);
    expect(state().conversations).toHaveLength(1);
    expect(messages()).toEqual([]);
    expect(Object.values(state().draftsByConversation)).toEqual([""]);
    rejectLate(new Error("late"));
    await Promise.resolve();
    expect(messages()).toEqual([]);
    expect(state().pendingRequest).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
