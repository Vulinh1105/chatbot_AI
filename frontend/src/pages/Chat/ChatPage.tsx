import { useRef } from "react";
import ConversationList from "../../components/chat/ConversationList";
import ChatInput from "../../components/chat/ChatInput";
import MessageList from "../../components/chat/MessageList";
import { useChatStore } from "../../stores/chatStore";
import "./ChatPage.css";
import { useChatSession } from "../../hooks/useChatSession";

function ChatPage() {
  useChatSession();

  const activeId = useChatStore(
    (state) => state.activeConversationId
  );

  const title = useChatStore(
    (state) =>
      state.conversations.find(
        (item) => item.id === state.activeConversationId
      )?.title
  );

  const conversations = useChatStore(
    (state) => state.conversations
  );

  const hasConversations =
    conversations.length > 0;

  const messages = useChatStore(
    (state) =>
      state.messagesByConversation[state.activeConversationId]
  );

  const draft = useChatStore(
    (state) =>
      state.draftsByConversation[state.activeConversationId]
  );

  const loading = useChatStore(
    (state) =>
      state.loadingHistory[state.activeConversationId]
  );

  const historyError = useChatStore(
    (state) =>
      state.historyErrors[state.activeConversationId]
  );

  const deleting = useChatStore(
    (state) =>
      state.deleting[state.activeConversationId]
  );

  const serverId = useChatStore(
    (state) =>
      state.serverIds[state.activeConversationId]
  );

  const pending = useChatStore(
    (state) => state.pendingRequest
  );

  const setDraft = useChatStore(
    (state) => state.setDraft
  );

  const handleSend = useChatStore(
    (state) => state.sendMessage
  );

  const loadHistory = useChatStore(
    (state) => state.loadHistory
  );

  const retry = useChatStore(
    (state) => state.retryMessage
  );

  const stop = useChatStore(
    (state) => state.stopRequest
  );

  const mobileListRef =
    useRef<HTMLDetailsElement>(null);

  const hasMessages =
    Boolean(messages && messages.length > 0);

  const isBusy =
    pending?.conversationId === activeId ||
    loading ||
    deleting;

  return (
    <section
      className="chat-page"
      aria-labelledby="chat-title"
    >
      {/* Mobile conversation selector */}
      <details
        className="conversation-mobile"
        ref={mobileListRef}
      >
        <summary>Hội thoại</summary>

        <ConversationList
          onSelected={() => {
            if (mobileListRef.current) {
              mobileListRef.current.open = false;

              mobileListRef.current
                .querySelector("summary")
                ?.focus();
            }
          }}
        />
      </details>

      {/* Chat header */}
      {hasConversations && (
        <header className="chat-page-header">
          <div>
            <h1 id="chat-title">
              {title || "Cuộc trò chuyện mới"}
            </h1>

            <p>
              Trao đổi và khám phá nội dung tài liệu của bạn.
            </p>
          </div>

          {serverId && (
            <button
              type="button"
              className="chat-history-reload"
              disabled={isBusy}
              onClick={() => {
                void loadHistory(activeId);
              }}
            >
              ↻ Tải lại
            </button>
          )}
        </header>
      )}

      {/* History error */}
      {historyError && (
        <div
          className="chat-history-error"
          role="alert"
        >
          <span>{historyError}</span>

          <button
            type="button"
            disabled={isBusy}
            onClick={() => {
              void loadHistory(activeId);
            }}
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Chat container */}
      <div className="chat-panel">
        <div className="chat-messages">
          {loading && !hasMessages ? (
            <div
              className="chat-state"
              role="status"
            >
              <div className="chat-state-spinner" />

              <strong>Đang tải cuộc trò chuyện</strong>

              <span>
                Vui lòng chờ một chút...
              </span>
            </div>
          ) : (
            <MessageList
              messages={messages ?? []}
              hasConversations={hasConversations}
              busy={pending !== null}
              onRetry={(messageId) => {
                retry(activeId, messageId);
              }}
            />
          )}
        </div>

        {/* AI response state */}
        {pending && (
          <div
            className="chat-stream-controls"
            role="status"
          >
            <div className="chat-pending">
              <span className="chat-pending-dot" />
              <span>
                {pending.conversationId === activeId
                  ? "Đang tạo câu trả lời..."
                  : "Đang tạo câu trả lời ở hội thoại khác..."}
              </span>
            </div>

            {pending.conversationId === activeId && (
              <button
                type="button"
                onClick={stop}
              >
                Dừng
              </button>
            )}
          </div>
        )}

        {/* Input */}
        <div className="chat-input-area">
          <ChatInput
            value={draft ?? ""}
            onChange={(value) => setDraft(activeId, value)}
            onSend={handleSend}
            disabled={
              pending?.conversationId === activeId ||
              loading ||
              deleting
            }
            sendDisabled={
              pending !== null ||
              loading ||
              deleting ||
              Boolean(historyError)
            }
          />
        </div>
      </div>
    </section>
  );
}

export default ChatPage;