import { useState } from "react";
import { useFeedbackStore } from "../stores/feedbackStore";
import "./ChatFeedbackButtons.css";

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
    <div className="chat-feedback">
      <div className="chat-feedback-buttons">
        <button
          type="button"
          disabled={alreadyRated || submitting}
          onClick={() => handleRate("up")}
          aria-pressed={rating === "up"}
          aria-label="Đánh giá hữu ích"
          className={`chat-feedback-btn${rating === "up" ? " is-up-active" : ""}`}
        >
          <ThumbUpIcon />
          Hữu ích
        </button>

        <button
          type="button"
          disabled={alreadyRated || submitting}
          onClick={() => setShowReasons(true)}
          aria-pressed={rating === "down"}
          aria-label="Đánh giá chưa hữu ích"
          className={`chat-feedback-btn${rating === "down" ? " is-down-active" : ""}`}
        >
          <ThumbDownIcon />
          Chưa hữu ích
        </button>
      </div>

      {showReasons && !alreadyRated && (
        <div className="chat-feedback-reasons">
          {DOWN_REASONS.map((reason) => (
            <button
              key={reason}
              type="button"
              disabled={submitting}
              onClick={() => handleRate("down", reason)}
              className="chat-feedback-reason-btn"
            >
              {reason}
            </button>
          ))}
        </div>
      )}

      {rating && !showReasons && (
        <p className="chat-feedback-thanks">Đã ghi nhận phản hồi, cảm ơn bạn</p>
      )}

      {error && <p className="chat-feedback-error">{error}</p>}
    </div>
  );
}

function ThumbUpIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M7 10v11M2 13v6a2 2 0 002 2h13.4a2 2 0 002-1.7l1.4-9a2 2 0 00-2-2.3H14V4a2 2 0 00-2-2c-.6 0-1.1.3-1.4.8L7 10H2z" />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M17 14V3M22 11V5a2 2 0 00-2-2H6.6a2 2 0 00-2 1.7l-1.4 9a2 2 0 002 2.3H10v4a2 2 0 002 2c.6 0 1.1-.3 1.4-.8L17 14h5z" />
    </svg>
  );
}
