import { beforeEach, expect, it, vi } from "vitest";
import api from "../src/services/api";
import { askQuestion, createChat, deleteChat, getChats, getMessages } from "../src/services/chatService";

vi.mock("../src/services/api", () => ({ default: { post: vi.fn(), get: vi.fn(), delete: vi.fn() } }));
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.post).mockResolvedValue({ data: { id: 7 } });
  vi.mocked(api.get).mockResolvedValue({ data: { items: [] } });
  vi.mocked(api.delete).mockResolvedValue({});
});
it("uses the backend request contract, cursor and cancellation signal", async () => {
  await createChat("Title");
  expect(api.post).toHaveBeenCalledWith("/api/v1/chats/", { title: "Title" });
  const controller = new AbortController();
  await askQuestion("7", "Question", controller.signal);
  expect(api.post).toHaveBeenCalledWith("/api/v1/chats/7/ask", { question: "Question" }, { signal: controller.signal, timeout: 120_000 });
  await getChats(12);
  expect(api.get).toHaveBeenCalledWith("/api/v1/chats/", { params: { limit: 100, cursor: 12 } });
  await getMessages("7", 100);
  expect(api.get).toHaveBeenCalledWith("/api/v1/chats/7/messages", { params: { limit: 100, cursor: 100 } });
  await deleteChat("7");
  expect(api.delete).toHaveBeenCalledWith("/api/v1/chats/7");
});
