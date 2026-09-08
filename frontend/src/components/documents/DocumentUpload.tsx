import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import api from "../../services/api";

type UploadStatus = "pending" | "processing" | "success" | "error";

interface UploadItem {
  id: string;
  file: File;
  status: UploadStatus;
  error?: string;
}

const MAX_FILE_SIZE = 20 * 1024 * 1024;

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/csv",
];

const getErrorMessage = (error: unknown): string => {
  const axiosError = error as {
    response?: {
      data?: {
        detail?: unknown;
      };
    };
    message?: string;
  };

  const detail = axiosError?.response?.data?.detail;

  // Backend trả lỗi dạng chuỗi
  if (typeof detail === "string") {
    return detail;
  }

  // FastAPI validation error thường trả về mảng object
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (
          typeof item === "object" &&
          item !== null &&
          "msg" in item
        ) {
          return String(
            (item as { msg?: unknown }).msg ?? "Dữ liệu không hợp lệ"
          );
        }

        return "Dữ liệu không hợp lệ";
      })
      .join(", ");
  }

  if (axiosError?.message) {
    return axiosError.message;
  }

  return "Tải tài liệu thất bại";
};

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getFileIcon = (file: File): string => {
  if (file.type === "application/pdf") {
    return "📕";
  }

  if (
    file.type ===
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ) {
    return "📘";
  }

  return "📄";
};

function DocumentUpload() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [items, setItems] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return "Chỉ hỗ trợ file PDF, DOCX, TXT hoặc CSV";
    }

    if (file.size > MAX_FILE_SIZE) {
      return "Kích thước file không được vượt quá 20MB";
    }

    return null;
  };

  const uploadFile = async (item: UploadItem) => {
    setItems((prev) =>
      prev.map((current) =>
        current.id === item.id
          ? {
              ...current,
              status: "processing",
              error: undefined,
            }
          : current
      )
    );

    try {
      const formData = new FormData();
      formData.append("file", item.file);

      await api.post("/api/v1/documents/", formData);

      setItems((prev) =>
        prev.map((current) =>
          current.id === item.id
            ? {
                ...current,
                status: "success",
                error: undefined,
              }
            : current
        )
      );
    } catch (error) {
      const message = getErrorMessage(error);

      setItems((prev) =>
        prev.map((current) =>
          current.id === item.id
            ? {
                ...current,
                status: "error",
                error: message,
              }
            : current
        )
      );
    }
  };

  const addFiles = (files: File[]) => {
    const newItems: UploadItem[] = [];

    files.forEach((file) => {
      const validationError = validateFile(file);

      const item: UploadItem = {
        id: `${file.name}-${file.lastModified}-${Math.random()}`,
        file,
        status: validationError ? "error" : "pending",
        error: validationError ?? undefined,
      };

      newItems.push(item);
    });

    setItems((prev) => [...prev, ...newItems]);

    // Chỉ upload những file hợp lệ
    newItems
      .filter((item) => item.status === "pending")
      .forEach((item) => {
        void uploadFile(item);
      });
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);

    if (files.length > 0) {
      addFiles(files);
    }

    // Cho phép chọn lại cùng một file
    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);

    const files = Array.from(event.dataTransfer.files);

    if (files.length > 0) {
      addFiles(files);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleRetry = (item: UploadItem) => {
    void uploadFile(item);
  };

  const handleRemove = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  return (
    <div className="document-upload">
      <div
        className={`document-upload-zone ${
          isDragging ? "document-upload-zone-dragging" : ""
        }`}
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          ref={inputRef}
          type="file"
          hidden
          multiple
          accept=".pdf,.docx,.txt,.csv"
          onChange={handleFileChange}
        />

        <div className="document-upload-icon">↑</div>

        <h3>Tải tài liệu lên</h3>

        <p>
          Kéo và thả file vào đây hoặc click để chọn file
        </p>

        <p>Hỗ trợ PDF, DOCX, TXT, CSV — tối đa 20MB</p>
      </div>

      {items.length > 0 && (
        <div className="document-upload-list">
          {items.map((item) => (
            <div className="document-upload-item" key={item.id}>
              <div className="document-file-info">
                <div className="document-file-icon">
                  {getFileIcon(item.file)}
                </div>

                <div>
                  <strong>{item.file.name}</strong>

                  <div>
                    {formatFileSize(item.file.size)}
                  </div>
                </div>
              </div>

              <div className="document-upload-status">
                {item.status === "pending" && (
                  <span>Đang chờ...</span>
                )}

                {item.status === "processing" && (
                  <span className="status-processing">
                    Đang tải lên...
                  </span>
                )}

                {item.status === "success" && (
                  <span className="status-success">
                    Tải lên thành công
                  </span>
                )}

                {item.status === "error" && (
                  <span className="status-error">
                    {item.error ?? "Tải lên thất bại"}
                  </span>
                )}
              </div>

              {item.status === "error" && (
                <button
                  type="button"
                  className="document-retry-button"
                  onClick={() => handleRetry(item)}
                >
                  Thử lại
                </button>
              )}

              <button
                type="button"
                className="document-remove-button"
                onClick={() => handleRemove(item.id)}
              >
                Xóa
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default DocumentUpload;