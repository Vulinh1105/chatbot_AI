import api from "./api";

export interface ApiChat {
  id: number;
  owner_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiMessage {
  id: number;
  chat_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  sources: {
    source: string;
    pages: number[];
    [key: string]: unknown;
  }[];
  status: string;
  created_at: string;
}

export interface ChatListResponse {
  items: ApiChat[];
  next_cursor: number | null;
  has_more: boolean;
}

export interface ChatHistoryResponse {
  chat: ApiChat;
  messages: ApiMessage[];
  next_cursor: number | null;
  has_more: boolean;
}

export async function createChat(title: string) {
  return (await api.post<ApiChat>("/api/v1/chats/", { title })).data;
}

export async function getChats(cursor?: number) {
  return (await api.get<ChatListResponse>("/api/v1/chats/", {
    params: { limit: 100, cursor },
  })).data;
}

export async function askQuestion(chatId: string, question: string, signal?: AbortSignal) {
  return (await api.post<ApiMessage>(`/api/v1/chats/${chatId}/ask`,
    { question }, { signal, timeout: 120_000 })).data;
}

export async function getMessages(chatId: string, cursor?: number) {
  return (await api.get<ChatHistoryResponse>(`/api/v1/chats/${chatId}/messages`, {
    params: { limit: 100, cursor },
  })).data;
}

export async function deleteChat(chatId: string) {
  await api.delete(`/api/v1/chats/${chatId}`);
}
