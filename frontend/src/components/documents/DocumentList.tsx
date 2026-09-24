import { useEffect, useState } from "react";
import type { Document } from "../../types/document";
import {
  deleteDocument,
  getDocuments,
} from "../../services/documentService";
import DeleteDocumentModal from "./DeleteDocumentModal";
import VersionHistoryModal from "./VersionHistoryModal";

interface DocumentListProps {
  refreshKey?: number;
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getDocumentIcon = (
  document: Document
): string => {
  const type =
    document.content_type?.toLowerCase() ?? "";

  const name =
    document.original_filename.toLowerCase();

  if (
    type.includes("pdf") ||
    name.endsWith(".pdf")
  ) {
    return "📕";
  }

  if (
    type.includes("word") ||
    type.includes("officedocument") ||
    name.endsWith(".docx")
  ) {
    return "📘";
  }

  if (
    type.includes("csv") ||
    name.endsWith(".csv")
  ) {
    return "📊";
  }

  return "📄";
};

const getDocumentType = (
  document: Document
): string => {
  const name =
    document.original_filename.toLowerCase();

  if (name.endsWith(".pdf")) {
    return "PDF";
  }

  if (name.endsWith(".docx")) {
    return "DOCX";
  }

  if (name.endsWith(".csv")) {
    return "CSV";
  }

  if (name.endsWith(".txt")) {
    return "TXT";
  }

  return "FILE";
};

const getErrorMessage = (
  error: unknown
): string => {
  const axiosError = error as {
    response?: {
      data?: {
        detail?: unknown;
      };
    };
    message?: string;
  };

  const detail =
    axiosError?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (
          typeof item === "object" &&
          item !== null &&
          "msg" in item
        ) {
          return String(
            (item as { msg?: unknown }).msg ??
              "Dữ liệu không hợp lệ"
          );
        }

        return "Dữ liệu không hợp lệ";
      })
      .join(", ");
  }

  return (
    axiosError?.message ||
    "Không thể thực hiện thao tác."
  );
};

function DocumentList({
  refreshKey = 0,
}: DocumentListProps) {
  const [documents, setDocuments] =
    useState<Document[]>([]);

  const [
    isLoading,
    setIsLoading,
  ] = useState(true);

  const [error, setError] =
    useState("");

  
  const [
    selectedDocument,
    setSelectedDocument,
  ] = useState<Document | null>(null);

  const [
    isDeleting,
    setIsDeleting,
  ] = useState(false);

  const [
    deleteError,
    setDeleteError,
  ] = useState("");

  
  const [
    versionDocument,
    setVersionDocument,
  ] = useState<Document | null>(null);

  const [
    successMessage,
    setSuccessMessage,
  ] = useState("");

  const fetchDocuments = async () => {
    try {
      setIsLoading(true);
      setError("");

      const data = await getDocuments();

      setDocuments(data);
    } catch (error) {
      setError(
        getErrorMessage(error) ||
          "Không thể tải danh sách tài liệu."
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadDocuments = async () => {
      try {
        const data = await getDocuments();

        if (!cancelled) {
          setDocuments(data);
          setError("");
        }
      } catch (error) {
        if (!cancelled) {
          setError(
            getErrorMessage(error) ||
              "Không thể tải danh sách tài liệu."
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadDocuments();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);


  const openDeleteModal = (
    document: Document
  ) => {
    setSelectedDocument(document);
    setDeleteError("");
  };

  const closeDeleteModal = () => {
    if (isDeleting) {
      return;
    }

    setSelectedDocument(null);
    setDeleteError("");
  };

  const handleDelete = async () => {
    if (!selectedDocument) {
      return;
    }

    try {
      setIsDeleting(true);
      setDeleteError("");

      await deleteDocument(
        selectedDocument.id
      );

      setDocuments((prev) =>
        prev.filter(
          (document) =>
            document.id !==
            selectedDocument.id
        )
      );

      const deletedName =
        selectedDocument.original_filename;

      setSelectedDocument(null);

      setSuccessMessage(
        `Đã xóa "${deletedName}" thành công.`
      );

      window.setTimeout(() => {
        setSuccessMessage("");
      }, 3000);
    } catch (error) {
      setDeleteError(
        getErrorMessage(error) ||
          "Không thể xóa tài liệu. Tài liệu có thể đang được xử lý, vui lòng thử lại sau."
      );
    } finally {
      setIsDeleting(false);
    }
  };


  const openVersionHistory = (
    document: Document
  ) => {
    setVersionDocument(document);
  };

  const closeVersionHistory = () => {
    setVersionDocument(null);
  };

  const handleRollbackSuccess = () => {
    setSuccessMessage(
      "Đã khôi phục phiên bản và hoàn tất re-index."
    );

    window.setTimeout(() => {
      setSuccessMessage("");
    }, 3000);
  };

  return (
    <>
      <div
        style={{
          marginTop: "32px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "16px",
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: "20px",
                color: "#f8fafc",
                fontWeight: 700,
                textShadow: "0 2px 10px rgba(0, 0, 0, 0.4)",
              }}
            >
              Tài liệu của bạn
            </h3>

            <p
              style={{
                margin: "5px 0 0",
                color: "#94a3b8",
                fontSize: "14px",
              }}
            >
              {documents.length} tài liệu
            </p>
          </div>

          <button
            type="button"
            onClick={() =>
              void fetchDocuments()
            }
            disabled={isLoading}
            style={{
              border: "1px solid rgba(117, 181, 255, 0.25)",
              background: "rgba(15, 28, 64, 0.65)",
              backdropFilter: "blur(8px)",
              WebkitBackdropFilter: "blur(8px)",
              borderRadius: "10px",
              padding: "8px 14px",
              color: "#93c5fd",
              cursor: "pointer",
              fontWeight: 600,
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.2)",
            }}
          >
            ↻ Làm mới
          </button>
        </div>

        {isLoading && (
          <div
            style={{
              padding: "36px",
              textAlign: "center",
              color: "#94a3b8",
              background: "rgba(10, 20, 50, 0.6)",
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              border: "1px solid rgba(117, 181, 255, 0.15)",
              borderRadius: "14px",
            }}
          >
            Đang tải danh sách tài liệu...
          </div>
        )}

        {!isLoading && error && (
          <div
            style={{
              padding: "16px",
              borderRadius: "12px",
              background: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#fca5a5",
            }}
          >
            <div>{error}</div>

            <button
              type="button"
              onClick={() =>
                void fetchDocuments()
              }
              style={{
                marginTop: "10px",
                border: "none",
                background: "transparent",
                color: "#f87171",
                fontWeight: 600,
                cursor: "pointer",
                padding: 0,
              }}
            >
              Thử lại
            </button>
          </div>
        )}

        {!isLoading &&
          !error &&
          documents.length === 0 && (
            <div
              style={{
                padding: "42px 20px",
                textAlign: "center",
                border: "1px dashed rgba(117, 181, 255, 0.25)",
                borderRadius: "14px",
                background: "rgba(10, 20, 50, 0.5)",
                backdropFilter: "blur(10px)",
                WebkitBackdropFilter: "blur(10px)",
              }}
            >
              <div
                style={{
                  fontSize: "40px",
                  marginBottom: "10px",
                }}
              >
                📂
              </div>

              <h4
                style={{
                  margin: "0 0 6px",
                  fontSize: "17px",
                  color: "#f8fafc",
                }}
              >
                Chưa có tài liệu
              </h4>

              <p
                style={{
                  margin: 0,
                  color: "#94a3b8",
                }}
              >
                Hãy tải tài liệu lên để
                bắt đầu.
              </p>
            </div>
          )}

        {!isLoading &&
          !error &&
          documents.length > 0 && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              {documents.map(
                (document) => (
                  <div
                    key={document.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "14px",
                      padding: "15px 18px",
                      background: "rgba(11, 25, 60, 0.72)",
                      backdropFilter: "blur(16px)",
                      WebkitBackdropFilter: "blur(16px)",
                      border:
                        "1px solid rgba(117, 181, 255, 0.18)",
                      borderRadius: "14px",
                      boxShadow: "0 6px 20px rgba(0, 0, 0, 0.2)",
                    }}
                  >
                    <div
                      style={{
                        width: "44px",
                        height: "44px",
                        borderRadius: "12px",
                        background:
                          "rgba(30, 48, 92, 0.6)",
                        border: "1px solid rgba(117, 181, 255, 0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "22px",
                        flexShrink: 0,
                      }}
                    >
                      {getDocumentIcon(
                        document
                      )}
                    </div>

                    <div
                      style={{
                        flex: 1,
                        minWidth: 0,
                      }}
                    >
                      <div
                        style={{
                          fontWeight: 600,
                          color: "#f8fafc",
                          fontSize: "15px",
                          overflow: "hidden",
                          textOverflow:
                            "ellipsis",
                          whiteSpace:
                            "nowrap",
                        }}
                        title={
                          document.original_filename
                        }
                      >
                        {
                          document.original_filename
                        }
                      </div>

                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "8px",
                          marginTop: "5px",
                          color: "#94a3b8",
                          fontSize: "13px",
                        }}
                      >
                        <span>
                          {getDocumentType(
                            document
                          )}
                        </span>

                        <span>•</span>

                        <span>
                          {formatFileSize(
                            document.size_bytes
                          )}
                        </span>

                        <span>•</span>

                        <span>
                          {new Date(
                            document.created_at
                          ).toLocaleDateString(
                            "vi-VN"
                          )}
                        </span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        openVersionHistory(
                          document
                        )
                      }
                      title="Lịch sử phiên bản"
                      style={{
                        width: "40px",
                        height: "40px",
                        border: "1px solid rgba(129, 140, 248, 0.3)",
                        borderRadius: "10px",
                        background:
                          "rgba(99, 102, 241, 0.18)",
                        color: "#a5b4fc",
                        cursor: "pointer",
                        fontSize: "18px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent:
                          "center",
                        flexShrink: 0,
                        transition: "all 0.18s ease",
                      }}
                    >
                      📜
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        openDeleteModal(
                          document
                        )
                      }
                      title="Xóa tài liệu"
                      style={{
                        width: "40px",
                        height: "40px",
                        border: "1px solid rgba(248, 113, 113, 0.3)",
                        borderRadius: "10px",
                        background:
                          "rgba(239, 68, 68, 0.15)",
                        color: "#fca5a5",
                        cursor: "pointer",
                        fontSize: "18px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent:
                          "center",
                        flexShrink: 0,
                        transition: "all 0.18s ease",
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                )
              )}
            </div>
          )}
      </div>

      {successMessage && (
        <div
          style={{
            position: "fixed",
            right: "24px",
            bottom: "24px",
            zIndex: 1001,
            background: "#166534",
            color: "#fff",
            padding: "14px 18px",
            borderRadius: "10px",
            boxShadow:
              "0 10px 30px rgba(0,0,0,0.15)",
            fontSize: "14px",
            fontWeight: 600,
          }}
        >
          ✓ {successMessage}
        </div>
      )}

      {selectedDocument && (
        <DeleteDocumentModal
          document={selectedDocument}
          isDeleting={isDeleting}
          error={deleteError}
          onCancel={closeDeleteModal}
          onConfirm={() =>
            void handleDelete()
          }
        />
      )}

      {versionDocument && (
        <VersionHistoryModal
          document={versionDocument}
          onClose={closeVersionHistory}
          onRollbackSuccess={
            handleRollbackSuccess
          }
        />
      )}
    </>
  );
}

export default DocumentList;