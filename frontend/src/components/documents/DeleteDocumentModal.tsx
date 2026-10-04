import type { Document } from "../../types/document";
import { createPortal } from "react-dom";

interface DeleteDocumentModalProps {
  document: Document;
  isDeleting: boolean;
  error: string;
  onCancel: () => void;
  onConfirm: () => void;
}

function DeleteDocumentModal({
  document,
  isDeleting,
  error,
  onCancel,
  onConfirm,
}: DeleteDocumentModalProps) {
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
        onClick={(event) =>
          event.stopPropagation()
        }
        style={{
          width: "100%",
          maxWidth: "440px",
          background: "linear-gradient(145deg, rgba(15, 25, 60, 0.98), rgba(9, 16, 42, 0.98))",
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
          Xóa tài liệu này?
        </h3>

        <p
          style={{
            margin: "0 auto",
            textAlign: "center",
            color: "#94a3b8",
            lineHeight: 1.6,
          }}
        >
          Bạn có chắc muốn xóa{" "}
          <strong
            style={{
              color: "#f1f5f9",
              wordBreak: "break-word",
            }}
          >
            "{document.original_filename}"
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
          ⚠️ Tài liệu sẽ bị xóa khỏi hệ thống và
          không thể hoàn tác.
        </div>

        {error && (
          <div
            style={{
              marginTop: "12px",
              padding: "12px 14px",
              borderRadius: "10px",
              background: "rgba(239, 68, 68, 0.15)",
              border:
                "1px solid rgba(239, 68, 68, 0.3)",
              color: "#fca5a5",
              fontSize: "13px",
              lineHeight: 1.5,
            }}
          >
            {error}
          </div>
        )}

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
              border:
                "1px solid rgba(117, 181, 255, 0.2)",
              borderRadius: "10px",
              background: "rgba(30, 48, 92, 0.4)",
              color: "#cbd5e1",
              fontWeight: 600,
              cursor: isDeleting
                ? "not-allowed"
                : "pointer",
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
              cursor: isDeleting
                ? "not-allowed"
                : "pointer",
              opacity: isDeleting ? 0.7 : 1,
              boxShadow: "0 4px 15px rgba(239, 68, 68, 0.3)",
              transition: "all 0.18s ease",
            }}
          >
            {isDeleting
              ? "Đang xóa..."
              : "Xóa tài liệu"}
          </button>
        </div>
      </div>
    </div>,
    window.document.body
  );
}

export default DeleteDocumentModal;