// src/components/ChatFeedbackButtons.tsx
import { useState } from "react";
import { useFeedbackStore } from "../stores/feedbackStore";

const DOWN_REASONS = [
  "Thông tin không chính xác",
  "Chưa trả lời đúng câu hỏi",
  "Thiếu chi tiết",
  "Khác",
];

interface ChatFeedbackButtonsProps {
  messageId: string;
  conversationId: string;
}

export default function ChatFeedbackButtons({
  messageId,
  conversationId,
}: ChatFeedbackButtonsProps) {
  const getFeedbackForMessage = useFeedbackStore((s) => s.getFeedbackForMessage);
  const submitFeedback = useFeedbackStore((s) => s.submitFeedback);

  const existing = getFeedbackForMessage(messageId);
  const [rating, setRating] = useState<"up" | "down" | null>(existing?.rating ?? null);
  const [showReasons, setShowReasons] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const alreadyRated = rating !== null;

  async function handleRate(newRating: "up" | "down", comment = "") {
    setSubmitting(true);
    setError(null);
    try {
      await submitFeedback(messageId, conversationId, newRating, comment);
      setRating(newRating);
      setShowReasons(false);
    } catch {
      setError("Không gửi được, thử lại nhé.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={alreadyRated || submitting}
          onClick={() => handleRate("up")}
          aria-pressed={rating === "up"}
          aria-label="Đánh giá hữu ích"
          className={[
            "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
            "disabled:cursor-default",
            rating === "up"
              ? "border-blue-200 bg-blue-50 text-blue-600"
              : "border-gray-200 bg-white text-gray-500 hover:bg-gray-50",
          ].join(" ")}
        >
          <ThumbUpIcon className="h-3.5 w-3.5" />
          Hữu ích
        </button>

        <button
          type="button"
          disabled={alreadyRated || submitting}
          onClick={() => setShowReasons(true)}
          aria-pressed={rating === "down"}
          aria-label="Đánh giá chưa hữu ích"
          className={[
            "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
            "disabled:cursor-default",
            rating === "down"
              ? "border-red-200 bg-red-50 text-red-600"
              : "border-gray-200 bg-white text-gray-500 hover:bg-gray-50",
          ].join(" ")}
        >
          <ThumbDownIcon className="h-3.5 w-3.5" />
          Chưa hữu ích
        </button>
      </div>

      {showReasons && !alreadyRated && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {DOWN_REASONS.map((reason) => (
            <button
              key={reason}
              type="button"
              disabled={submitting}
              onClick={() => handleRate("down", reason)}
              className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
            >
              {reason}
            </button>
          ))}
        </div>
      )}

      {rating && !showReasons && (
        <p className="mt-1.5 text-xs text-gray-400">Đã ghi nhận phản hồi, cảm ơn bạn</p>
      )}

      {error && <p className="mt-1.5 text-xs text-red-500">{error}</p>}
    </div>
  );
}

function ThumbUpIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="M7 10v11M2 13v6a2 2 0 002 2h13.4a2 2 0 002-1.7l1.4-9a2 2 0 00-2-2.3H14V4a2 2 0 00-2-2c-.6 0-1.1.3-1.4.8L7 10H2z" />
    </svg>
  );
}

function ThumbDownIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="M17 14V3M22 11V5a2 2 0 00-2-2H6.6a2 2 0 00-2 1.7l-1.4 9a2 2 0 002 2.3H10v4a2 2 0 002 2c.6 0 1.1-.3 1.4-.8L17 14h5z" />
    </svg>
  );
}
