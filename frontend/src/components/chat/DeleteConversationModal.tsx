import { useEffect } from "react";
import { createPortal } from "react-dom";

interface DeleteConversationModalProps {
  conversationTitle: string;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

/**
 * Modal xác nhận trước khi xóa cuộc trò chuyện, ngăn chặn thao tác nhầm lẫn
 */
function DeleteConversationModal({
  conversationTitle,
  isDeleting,
  onCancel,
  onConfirm,
}: DeleteConversationModalProps) {
  // Lắng nghe phím Escape để đóng modal an toàn
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isDeleting) {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDeleting, onCancel]);

  return createPortal(
    <div
      onClick={() => {
        if (!isDeleting) {
          onCancel();
        }
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(3, 7, 18, 0.72)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        zIndex: 99999,
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "440px",
          background:
            "linear-gradient(145deg, rgba(15, 25, 60, 0.98), rgba(9, 16, 42, 0.98))",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(117, 181, 255, 0.22)",
          borderRadius: "20px",
          padding: "28px",
          boxShadow:
            "0 25px 60px rgba(0, 0, 0, 0.5), 0 0 35px rgba(56, 189, 248, 0.1)",
        }}
      >
        <div
          style={{
            width: "60px",
            height: "60px",
            margin: "0 auto 18px",
            borderRadius: "16px",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "28px",
          }}
        >
          🗑️
        </div>

        <h3
          style={{
            margin: "0 0 10px",
            textAlign: "center",
            fontSize: "21px",
            color: "#f8fafc",
            fontWeight: 700,
          }}
        >
          Xóa cuộc trò chuyện này?
        </h3>

        <p
          style={{
            margin: "0 auto",
            textAlign: "center",
            color: "#94a3b8",
            lineHeight: 1.6,
          }}
        >
          Bạn có chắc muốn xóa cuộc trò chuyện{" "}
          <strong
            style={{
              color: "#f1f5f9",
              wordBreak: "break-word",
            }}
          >
            "{conversationTitle || "Cuộc trò chuyện"}"
          </strong>
          ?
        </p>

        <div
          style={{
            marginTop: "20px",
            padding: "13px 14px",
            borderRadius: "10px",
            background: "rgba(245, 158, 11, 0.12)",
            border: "1px solid rgba(245, 158, 11, 0.28)",
            color: "#fde68a",
            fontSize: "13px",
            lineHeight: 1.5,
          }}
        >
          ⚠️ Toàn bộ tin nhắn trong cuộc trò chuyện sẽ bị xóa vĩnh viễn và không thể hoàn tác.
        </div>

        <div
          style={{
            display: "flex",
            gap: "10px",
            marginTop: "24px",
          }}
        >
          <button
            type="button"
            disabled={isDeleting}
            onClick={onCancel}
            style={{
              flex: 1,
              height: "44px",
              border: "1px solid rgba(117, 181, 255, 0.2)",
              borderRadius: "10px",
              background: "rgba(30, 48, 92, 0.4)",
              color: "#cbd5e1",
              fontWeight: 600,
              cursor: isDeleting ? "not-allowed" : "pointer",
              opacity: isDeleting ? 0.6 : 1,
              transition: "all 0.18s ease",
            }}
          >
            Hủy
          </button>

          <button
            type="button"
            disabled={isDeleting}
            onClick={onConfirm}
            style={{
              flex: 1,
              height: "44px",
              border: "none",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #ef4444, #dc2626)",
              color: "#fff",
              fontWeight: 600,
              cursor: isDeleting ? "not-allowed" : "pointer",
              opacity: isDeleting ? 0.7 : 1,
              boxShadow: "0 4px 15px rgba(239, 68, 68, 0.3)",
              transition: "all 0.18s ease",
            }}
          >
            {isDeleting ? "Đang xóa..." : "Xóa trò chuyện"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

export default DeleteConversationModal;
