// src/stores/feedbackStore.ts
import { create } from "zustand";
import * as feedbackService from "../services/feedbackService";
import type {
  FeedbackRating,
  FeedbackItem,
  FeedbackStats,
  FeedbackFilter,
} from "../services/feedbackService";

interface FeedbackEntry {
  rating: FeedbackRating;
  comment?: string;
}

interface FeedbackState {
  feedbackByMessageId: Record<string, FeedbackEntry>;

  adminItems: FeedbackItem[];
  adminStats: FeedbackStats;
  adminLoading: boolean;
  adminError: string | null;

  getFeedbackForMessage: (messageId: string) => FeedbackEntry | null;
  submitFeedback: (
    messageId: string,
    conversationId: string,
    rating: FeedbackRating,
    comment?: string
  ) => Promise<void>;
  loadAdminFeedback: (filter?: FeedbackFilter) => Promise<void>;
  resetFeedback: () => void;
}

const emptyStats: FeedbackStats = { total: 0, upCount: 0, downCount: 0 };

export const useFeedbackStore = create<FeedbackState>((set, get) => ({
  feedbackByMessageId: {},

  adminItems: [],
  adminStats: emptyStats,
  adminLoading: false,
  adminError: null,

  getFeedbackForMessage: (messageId) => get().feedbackByMessageId[messageId] ?? null,

  submitFeedback: async (messageId, conversationId, rating, comment = "") => {
    await feedbackService.submitFeedback({
      messageId,
      conversationId,
      rating,
      comment,
    });

    set((state) => ({
      feedbackByMessageId: {
        ...state.feedbackByMessageId,
        [messageId]: { rating, comment },
      },
    }));
  },

  loadAdminFeedback: async (filter: FeedbackFilter = "all") => {
    set({ adminLoading: true, adminError: null });
    try {
      const data = await feedbackService.fetchFeedbackList({ filter });
      set({
        adminItems: data.items ?? [],
        adminStats: data.stats ?? emptyStats,
        adminLoading: false,
      });
    } catch {
      set({ adminError: "Không tải được dữ liệu feedback.", adminLoading: false });
    }
  },

  resetFeedback: () =>
    set({
      feedbackByMessageId: {},
      adminItems: [],
      adminStats: emptyStats,
      adminError: null,
    }),
}));
