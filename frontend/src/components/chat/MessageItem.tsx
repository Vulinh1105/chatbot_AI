import { memo } from "react";
import type { Message } from "../../types/chat";
import { AnswerWithCitations } from "../citations/AnswerCitations";

const roleLabels = { user: "Bạn", assistant: "DocBot", system: "Hệ thống" };

function MessageItem({ message, onRetry, busy = false }: { message: Message; onRetry?: (id: string) => void; busy?: boolean }) {
  return (
    <li className={`chat-message chat-message-${message.role}`}>
      <article aria-label={`Tin nhắn từ ${roleLabels[message.role]}`}>
        <h3 className="chat-message-author">{roleLabels[message.role]}</h3>
        <div className="chat-message-body">
          {message.status === "waiting" && <p className="chat-waiting" role="status">Đang trả lời…</p>}
          {message.status === "streaming" && <p className="chat-waiting" role="status">Đang viết…</p>}
          {message.status === "stopped" && <p className="chat-waiting" role="status">Đã dừng</p>}
          {message.status === "error" && (
            <div className="chat-reply-error">
              <p role="alert">{message.error ?? "Không thể nhận câu trả lời."}</p>
              {onRetry && <button type="button" disabled={busy} onClick={() => onRetry(message.id)}>Thử lại</button>}
            </div>
          )}
          {message.role === "assistant" ? (
            <AnswerWithCitations content={message.content} citations={message.citations} />
          ) : (
            <p className="chat-message-text">{message.content}</p>
          )}
        </div>
      </article>
    </li>
  );
}

export default memo(MessageItem);
