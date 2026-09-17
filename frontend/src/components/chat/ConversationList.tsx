import { useRef } from "react";
import { useChatStore } from "../../stores/chatStore";
import "./ConversationList.css";

function ConversationList({ onSelected }: { onSelected?: () => void }) {
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const conversations = useChatStore((state) => state.conversations);
  const activeId = useChatStore((state) => state.activeConversationId);
  const select = useChatStore((state) => state.selectConversation);
  const create = useChatStore((state) => state.startNewConversation);
  const loading = useChatStore((state) => state.loadingConversations);
  const error = useChatStore((state) => state.error);
  const deleting = useChatStore((state) => state.deleting);
  const reload = useChatStore((state) => state.loadConversations);
  const remove = useChatStore((state) => state.deleteConversation);

  console.log("CONVERSATIONS:", conversations);
  console.log("ACTIVE ID:", activeId);

  return (
    <section className="conversation-panel" aria-label="Hội thoại">
      <button ref={newButtonRef} className="conversation-new" type="button" onClick={() => { create(); onSelected?.(); }}>
        + Cuộc trò chuyện mới
      </button>
      <h2>Hội thoại</h2>
      {loading && <p role="status">Đang tải hội thoại…</p>}
      {error && <div role="alert"><p>{error}</p><button type="button" disabled={loading} onClick={() => void reload()}>Tải lại danh sách</button></div>}
      <ul className="conversation-list">
        {conversations.map((conversation) => (
          <li key={conversation.id} className={`conversation-row${activeId === conversation.id ? " active" : ""}`}>
            <button
              type="button"
              className={`conversation-item${activeId === conversation.id ? " active" : ""}`}
              aria-current={activeId === conversation.id ? "true" : undefined}
              disabled={deleting[conversation.id]}
              title={conversation.title}
              onClick={() => { select(conversation.id); onSelected?.(); }}
            >
              {conversation.title}
            </button>
            <button
              type="button"
              className="conversation-delete"
              aria-label={`Xóa hội thoại: ${conversation.title}`}
              title="Xóa hội thoại"
              disabled={deleting[conversation.id]}
              onClick={() => { void remove(conversation.id); newButtonRef.current?.focus(); onSelected?.(); }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
                <path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7" />
              </svg>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default ConversationList;
