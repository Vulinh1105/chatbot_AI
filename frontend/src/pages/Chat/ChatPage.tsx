import { useRef } from "react";
import ConversationList from "../../components/chat/ConversationList";
import ChatInput from "../../components/chat/ChatInput";
import MessageList from "../../components/chat/MessageList";
import { useChatStore } from "../../stores/chatStore";
import "./ChatPage.css";
import { useChatSession } from "../../hooks/useChatSession";

function ChatPage() {
  useChatSession();

  const loading = useChatStore((state) => state.loadingHistory[state.activeConversationId]);
  const historyError = useChatStore((state) => state.historyErrors[state.activeConversationId]);
  const deleting = useChatStore((state) => state.deleting[state.activeConversationId]);
  const serverId = useChatStore((state) => state.serverIds[state.activeConversationId]);
  const loadHistory = useChatStore((state) => state.loadHistory);
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


      {serverId && <button type="button" disabled={loading || deleting || pending?.conversationId === activeId}
        onClick={() => void loadHistory(activeId)}>Tải lại lịch sử</button>}
      {loading && <p role="status">Đang tải lịch sử…</p>}
      {historyError && <p role="alert">{historyError}</p>}
      <div className="chat-panel">
        <MessageList
          messages={messages ?? []}
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
              Dừng chờ
            </button>
          </div>
        )}

        <ChatInput
          value={draft ?? ""}
          onChange={(value) => setDraft(activeId, value)}
          onSend={handleSend}
          disabled={pending?.conversationId === activeId || loading || deleting}
          sendDisabled={pending !== null || loading || deleting || Boolean(historyError)}
        />
      </div>
    </section>
  );
}

export default ChatPage;