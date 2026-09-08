import { useCallback, useLayoutEffect, useRef } from "react";
import type { Message } from "../../types/chat";
import MessageItem from "./MessageItem";
import "./MessageList.css";

export interface MessageListProps {
  messages: Message[];
  busy?: boolean;
  onRetry?: (id: string) => void;
}

function MessageList({ messages, busy = false, onRetry }: MessageListProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const bottomButtonRef = useRef<HTMLButtonElement>(null);
  const followingRef = useRef(true);
  const lastUserIdRef = useRef<string | undefined>(undefined);

  const updatePosition = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const nearBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <= 80;
    followingRef.current = nearBottom;
    if (bottomButtonRef.current) bottomButtonRef.current.hidden = nearBottom;
  }, []);

  const scrollToBottom = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
    updatePosition();
  }, [updatePosition]);

  useLayoutEffect(() => {
    const latestUserId = messages.findLast((message) => message.role === "user")?.id;
    const userSent = latestUserId !== lastUserIdRef.current && latestUserId !== undefined;
    lastUserIdRef.current = latestUserId;
    if (userSent || followingRef.current) scrollToBottom();
    else updatePosition();
  }, [messages, scrollToBottom, updatePosition]);

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    const content = contentRef.current;
    if (!viewport || !content) return;
    const observer = new ResizeObserver(() => {
      if (followingRef.current) scrollToBottom();
      else updatePosition();
    });
    observer.observe(viewport);
    observer.observe(content);
    return () => observer.disconnect();
  }, [scrollToBottom, updatePosition]);

  return (
    <section className="chat-message-region" aria-label="Cuộc trò chuyện">
      <div
        ref={viewportRef}
        className="chat-messages"
        role="log"
        aria-label="Danh sách tin nhắn"
        aria-live="polite"
        aria-relevant="additions text"
        tabIndex={0}
        onScroll={updatePosition}
      >
        <div ref={contentRef} className="chat-message-content">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <h3>Chưa có tin nhắn</h3>
              <p>Gửi câu hỏi để bắt đầu cuộc trò chuyện.</p>
            </div>
          ) : (
            <ol className="chat-message-list">
              {messages.map((message, index) => <MessageItem key={message.id} message={message} onRetry={index === messages.length - 1 ? onRetry : undefined} busy={busy} />)}
            </ol>
          )}
        </div>
      </div>
      <button ref={bottomButtonRef} type="button" className="chat-scroll-bottom" hidden onClick={scrollToBottom}>
        Xuống cuối
      </button>
    </section>
  );
}

export default MessageList;
