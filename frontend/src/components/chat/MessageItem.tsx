import { memo } from "react";
import type { Message } from "../../types/chat";
import { AnswerWithCitations } from "../citations/AnswerCitations";
import ChatFeedbackButtons from "../ChatFeedbackButtons";
import { useChatStore } from "../../stores/chatStore";

const roleLabels = {
  user: "Bạn",
  assistant: "DocBot",
  system: "Hệ thống",
};

function MessageItem({
  message,
  onRetry,
  busy = false,
}: {
  message: Message;
  onRetry?: (id: string) => void;
  busy?: boolean;
}) {
  const conversationId = useChatStore(
    (state) => state.activeConversationId
  );

  const serverId = useChatStore(
    (state) => state.serverIds[conversationId]
  );

  const showFeedback =
    message.role === "assistant" &&
    message.status !== "waiting" &&
    message.status !== "streaming" &&
    message.status !== "error";

  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <li
      className={`chat-message chat-message-${message.role}`}
    >
      <article
        className="chat-message-card"
        aria-label={`Tin nhắn từ ${roleLabels[message.role]}`}
      >
        <div className="chat-message-header">
          <div
            className="chat-message-avatar"
            aria-hidden="true"
          >
            {isUser ? "Bạn" : "D"}
          </div>

          <span className="chat-message-author">
            {roleLabels[message.role]}
          </span>
        </div>

        <div className="chat-message-body">
          {message.status === "waiting" && (
            <div
              className="chat-message-status"
              role="status"
            >
              <span className="chat-message-dots">
                <span />
                <span />
                <span />
              </span>

              <span>Đang chuẩn bị câu trả lời...</span>
            </div>
          )}

          {message.status === "streaming" && (
            <div
              className="chat-message-status"
              role="status"
            >
              <span className="chat-message-dots">
                <span />
                <span />
                <span />
              </span>

              <span>DocBot đang viết...</span>
            </div>
          )}

          {message.status === "stopped" && (
            <p className="chat-message-stopped">
              Đã dừng tạo câu trả lời
            </p>
          )}

          {message.status === "error" && (
            <div
              className="chat-reply-error"
              role="alert"
            >
              <div>
                <strong>Không thể nhận câu trả lời</strong>

                <p>
                  {message.error ??
                    "Đã xảy ra lỗi khi xử lý yêu cầu."}
                </p>
              </div>

              {onRetry && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onRetry(message.id)}
                >
                  Thử lại
                </button>
              )}
            </div>
          )}

          {isAssistant ? (
            <AnswerWithCitations
              content={message.content}
              citations={message.citations}
            />
          ) : (
            <p className="chat-message-text">
              {message.content}
            </p>
          )}

          {message.sources &&
            message.sources.length > 0 && (
              <div className="chat-message-sources">
                <span className="chat-sources-label">
                  Nguồn tham khảo
                </span>

                <ul>
                  {message.sources.map(
                    (source, index) => (
                      <li
                        key={`${source.source}-${index}`}
                      >
                        <span>
                          {source.source}
                        </span>

                        {source.pages.length > 0 && (
                          <span className="chat-source-pages">
                            Trang{" "}
                            {source.pages.join(", ")}
                          </span>
                        )}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}
        </div>

        {showFeedback && serverId && (
          <div className="chat-message-feedback">
            <ChatFeedbackButtons
              messageId={message.id}
              conversationId={serverId}
            />
          </div>
        )}
      </article>
    </li>
  );
}

export default memo(MessageItem);