import { useRef, useState } from "react";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB

interface UploadItem {
  id: string;
  file: File;
  status: "pending" | "processing" | "success" | "error";
  error?: string;
}

function DocumentUpload() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return "Chỉ hỗ trợ file PDF, TXT hoặc DOCX.";
    }

    if (file.size > MAX_FILE_SIZE) {
      return "Dung lượng file không được vượt quá 20MB.";
    }

    return null;
  };

  const uploadFile = async (item: UploadItem) => {
    setItems((current) =>
      current.map((uploadItem) =>
        uploadItem.id === item.id
          ? {
              ...uploadItem,
              status: "processing",
              error: undefined,
            }
          : uploadItem
      )
    );

    try {
      // Mock upload.
      // Sau này thay bằng API backend thật.
      await new Promise((resolve) => setTimeout(resolve, 1200));

      setItems((current) =>
        current.map((uploadItem) =>
          uploadItem.id === item.id
            ? {
                ...uploadItem,
                status: "success",
              }
            : uploadItem
        )
      );
    } catch {
      setItems((current) =>
        current.map((uploadItem) =>
          uploadItem.id === item.id
            ? {
                ...uploadItem,
                status: "error",
                error: "Upload thất bại. Vui lòng thử lại.",
              }
            : uploadItem
        )
      );
    }
  };

  const handleFiles = (files: FileList | File[]) => {
    const fileArray = Array.from(files);

    const newItems: UploadItem[] = fileArray.map((file) => {
      const error = validateFile(file);

      return {
        id: `${file.name}-${file.lastModified}-${Math.random()}`,
        file,
        status: error ? "error" : "pending",
        error: error || undefined,
      };
    });

    setItems((current) => [...current, ...newItems]);

    newItems
      .filter((item) => item.status === "pending")
      .forEach((item) => {
        void uploadFile(item);
      });
  };

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (event.target.files) {
      handleFiles(event.target.files);
    }

    event.target.value = "";
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);

    if (event.dataTransfer.files.length > 0) {
      handleFiles(event.dataTransfer.files);
    }
  };

  const handleRetry = (item: UploadItem) => {
    void uploadFile(item);
  };

  const removeItem = (id: string) => {
    setItems((current) =>
      current.filter((item) => item.id !== id)
    );
  };

  const formatFileSize = (size: number) => {
    if (size < 1024) {
      return `${size} B`;
    }

    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <section className="document-upload">
      <div
        className={`document-upload-zone ${
          isDragging ? "dragging" : ""
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            inputRef.current?.click();
          }
        }}
      >
        <div className="document-upload-icon">↑</div>

        <h3>Tải tài liệu lên</h3>

        <p>
          Kéo & thả file vào đây hoặc{" "}
          <span className="document-upload-link">
            chọn file
          </span>
        </p>

        <small>
          Hỗ trợ PDF, TXT, DOCX · Tối đa 20MB/file
        </small>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.docx"
          multiple
          hidden
          onChange={handleInputChange}
        />
      </div>

      {items.length > 0 && (
        <div className="document-upload-list">
          {items.map((item) => (
            <div
              className="document-upload-item"
              key={item.id}
            >
              <div className="document-file-info">
                <div className="document-file-icon">
                  {item.file.name
                    .toLowerCase()
                    .endsWith(".pdf")
                    ? "PDF"
                    : item.file.name
                        .toLowerCase()
                        .endsWith(".docx")
                    ? "DOCX"
                    : "TXT"}
                </div>

                <div>
                  <strong>{item.file.name}</strong>
                  <span>
                    {formatFileSize(item.file.size)}
                  </span>
                </div>
              </div>

              <div className="document-upload-status">
                {item.status === "pending" && (
                  <span>Đang chờ...</span>
                )}

                {item.status === "processing" && (
                  <span className="status-processing">
                    Đang upload...
                  </span>
                )}

                {item.status === "success" && (
                  <span className="status-success">
                    ✓ Upload thành công
                  </span>
                )}

                {item.status === "error" && (
                  <div className="status-error">
                    <span>{item.error}</span>

                    {item.error ===
                      "Upload thất bại. Vui lòng thử lại." && (
                      <button
                        type="button"
                        onClick={() => handleRetry(item)}
                      >
                        Retry
                      </button>
                    )}
                  </div>
                )}

                {item.status !== "processing" && (
                  <button
                    type="button"
                    className="document-remove-button"
                    onClick={() => removeItem(item.id)}
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default DocumentUpload;