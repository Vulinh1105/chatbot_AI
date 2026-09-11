// src/services/feedbackService.ts

export type FeedbackRating = "up" | "down";

export interface SubmitFeedbackInput {
  messageId: string;
  conversationId: string;
  rating: FeedbackRating;
  comment?: string;
}

export interface FeedbackItem {
  id: string;
  messageId: string;
  question: string;
  rating: FeedbackRating;
  comment?: string;
  userId: string;
  createdAt: string; // ISO date string
}

export interface FeedbackStats {
  total: number;
  upCount: number;
  downCount: number;
}

export interface FeedbackListResponse {
  items: FeedbackItem[];
  total: number;
  stats: FeedbackStats;
}

export type FeedbackFilter = "all" | FeedbackRating;

interface FetchFeedbackListParams {
  filter?: FeedbackFilter;
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/api/feedback";

// Đổi BASE_URL và request thật khi backend sẵn sàng.
export async function submitFeedback(
  input: SubmitFeedbackInput
): Promise<{ id: string }> {
  const res = await fetch(BASE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...input,
      timestamp: new Date().toISOString(),
    }),
  });

  if (!res.ok) {
    throw new Error(`Gửi feedback thất bại: ${res.status}`);
  }
  return res.json();
}

export async function fetchFeedbackList(
  params: FetchFeedbackListParams = {}
): Promise<FeedbackListResponse> {
  const { filter = "all", page, pageSize } = params;

  const query = new URLSearchParams(
    Object.entries({ filter, page, pageSize })
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();

  const res = await fetch(`${BASE_URL}?${query}`);
  if (!res.ok) {
    throw new Error(`Lấy danh sách feedback thất bại: ${res.status}`);
  }
  return res.json();
}
