import type { Document } from "../../types/document";

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
  return (
    <div
      onClick={() => {
        if (!isDeleting) {
          onCancel();
        }
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 23, 42, 0.55)",
        backdropFilter: "blur(3px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
        zIndex: 1000,
      }}
    >
      <div
        onClick={(event) =>
          event.stopPropagation()
        }
        style={{
          width: "100%",
          maxWidth: "440px",
          background: "#fff",
          borderRadius: "18px",
          padding: "28px",
          boxShadow:
            "0 25px 60px rgba(0,0,0,0.2)",
        }}
      >
        <div
          style={{
            width: "60px",
            height: "60px",
            margin: "0 auto 18px",
            borderRadius: "16px",
            background: "#fef2f2",
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
            color: "#0f172a",
          }}
        >
          Xóa tài liệu này?
        </h3>

        <p
          style={{
            margin: "0 auto",
            textAlign: "center",
            color: "#64748b",
            lineHeight: 1.6,
          }}
        >
          Bạn có chắc muốn xóa{" "}
          <strong
            style={{
              color: "#1e293b",
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
            background: "#fff7ed",
            border: "1px solid #fed7aa",
            color: "#9a3412",
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
              background: "#fef2f2",
              border:
                "1px solid #fecaca",
              color: "#dc2626",
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
            marginTop: "22px",
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
                "1px solid #cbd5e1",
              borderRadius: "10px",
              background: "#fff",
              color: "#334155",
              fontWeight: 600,
              cursor: isDeleting
                ? "not-allowed"
                : "pointer",
              opacity: isDeleting ? 0.6 : 1,
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
              background: "#dc2626",
              color: "#fff",
              fontWeight: 600,
              cursor: isDeleting
                ? "not-allowed"
                : "pointer",
              opacity: isDeleting ? 0.7 : 1,
            }}
          >
            {isDeleting
              ? "Đang xóa..."
              : "Xóa tài liệu"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default DeleteDocumentModal;