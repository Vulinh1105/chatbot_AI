import { useRef } from "react";
import ConversationList from "../../components/chat/ConversationList";
import ChatInput from "../../components/chat/ChatInput";
import MessageList from "../../components/chat/MessageList";
import { useChatStore } from "../../stores/chatStore";
import "./ChatPage.css";
import { useChatSession } from "../../hooks/useChatSession";

function ChatPage() {
  useChatSession();

  const pending = useChatStore((state) => state.pendingRequest);
  const retry = useChatStore((state) => state.retryMessage);
  const stop = useChatStore((state) => state.stopRequest);
  const mobileListRef = useRef<HTMLDetailsElement>(null);
  const activeId = useChatStore((state) => state.activeConversationId);
  const draft = useChatStore(
    (state) => state.draftsByConversation[state.activeConversationId]
  );
  const setDraft = useChatStore((state) => state.setDraft);
  const messages = useChatStore(
    (state) => state.messagesByConversation[state.activeConversationId]
  );
  const title = useChatStore(
    (state) =>
      state.conversations.find(
        (item) => item.id === state.activeConversationId
      )?.title
  );
  const handleSend = useChatStore((state) => state.sendMessage);

  return (
    <section className="chat-page" aria-labelledby="chat-title">
      <header className="chat-page-header">
        <h2 id="chat-title">{title}</h2>
        <p>Trao đổi và khám phá nội dung tài liệu của bạn.</p>
      </header>

      <details className="conversation-mobile" ref={mobileListRef}>
        <summary>Hội thoại</summary>
        <ConversationList
          onSelected={() => {
            if (mobileListRef.current) {
              mobileListRef.current.open = false;
              mobileListRef.current.querySelector("summary")?.focus();
            }
          }}
        />
      </details>
      */

      <div className="chat-panel">
        <MessageList
          messages={messages}
          busy={pending !== null}
          onRetry={(id) => {
            retry(activeId, id);
          }}
        />

        {pending && (
          <div className="chat-stream-controls">
            <p className="chat-pending-note" role="status">
              {pending.conversationId === activeId
                ? "Đang tạo câu trả lời…"
                : "Đang tạo câu trả lời ở hội thoại khác…"}
            </p>

            <button type="button" onClick={stop}>
              Dừng
            </button>
          </div>
        )}

        <ChatInput
          value={draft}
          onChange={(value) => setDraft(activeId, value)}
          onSend={handleSend}
          disabled={pending?.conversationId === activeId}
          sendDisabled={pending !== null}
        />
      </div>
    </section>
  );
}

export default ChatPage;