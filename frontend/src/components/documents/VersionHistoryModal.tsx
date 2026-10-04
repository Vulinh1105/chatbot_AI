import { useEffect, useState } from "react";
import type {
  Document,
  DocumentVersion,
} from "../../types/document";
import {
  getMockDocumentVersions,
  mockRollbackDocumentVersion,
} from "../../services/documentService";
import "./VersionHistoryModal.css";

interface VersionHistoryModalProps {
  document: Document;
  onClose: () => void;
  onRollbackSuccess?: () => void;
}

function VersionHistoryModal({
  document,
  onClose,
  onRollbackSuccess,
}: VersionHistoryModalProps) {
  const [versions, setVersions] = useState<
    DocumentVersion[]
  >([]);

  const [loading, setLoading] = useState(true);

  const [selectedVersion, setSelectedVersion] =
    useState<DocumentVersion | null>(null);

  const [rollingBack, setRollingBack] =
    useState(false);

  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const loadVersions = async () => {
      try {
        setLoading(true);
        setError("");

        const data =
          await getMockDocumentVersions(
            document.id
          );

        if (!cancelled) {
          setVersions(data);
        }
      } catch {
        if (!cancelled) {
          setError(
            "Không thể tải lịch sử phiên bản."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadVersions();

    return () => {
      cancelled = true;
    };
  }, [document.id]);

  const handleRollback = async () => {
    if (
      !selectedVersion ||
      !selectedVersion.available
    ) {
      return;
    }

    try {
      setRollingBack(true);
      setError("");

      await mockRollbackDocumentVersion(
        document.id,
        selectedVersion.id
      );

      setVersions((currentVersions) =>
        currentVersions.map((version) => ({
          ...version,
          is_current:
            version.id === selectedVersion.id,
        }))
      );

      setSelectedVersion(null);

      onRollbackSuccess?.();
    } catch {
      setError(
        "Không thể khôi phục phiên bản."
      );
    } finally {
      setRollingBack(false);
    }
  };

  return (
    <div className="version-modal-overlay">
      <div className="version-modal">
        <div className="version-modal-header">
          <div>
            <h3>Lịch sử phiên bản</h3>

            <p>
              {document.original_filename}
            </p>
          </div>

          <button
            type="button"
            className="version-modal-close"
            onClick={onClose}
            disabled={rollingBack}
            aria-label="Đóng"
          >
            ×
          </button>
        </div>

        <div className="version-modal-body">
          {loading && (
            <div className="version-loading">
              Đang tải lịch sử phiên bản...
            </div>
          )}

          {!loading && error && (
            <div className="version-error">
              {error}
            </div>
          )}

          {!loading &&
            !error &&
            versions.length === 0 && (
              <div className="version-empty">
                Chưa có lịch sử phiên bản.
              </div>
            )}

          {!loading &&
            !error &&
            versions.length > 0 && (
              <div className="version-list">
                {versions.map((version) => (
                  <div
                    key={version.id}
                    className={`version-item ${
                      version.is_current
                        ? "version-item-current"
                        : ""
                    }`}
                  >
                    <div className="version-info">
                      <div className="version-title">
                        <strong>
                          Version{" "}
                          {version.version_number}
                        </strong>

                        {version.is_current && (
                          <span className="version-current-badge">
                            Hiện tại
                          </span>
                        )}
                      </div>

                      <div className="version-date">
                        Cập nhật:{" "}
                        {new Date(
                          version.updated_at
                        ).toLocaleString(
                          "vi-VN"
                        )}
                      </div>

                      {!version.available && (
                        <div className="version-unavailable">
                          Tệp phiên bản cũ không
                          còn khả dụng
                        </div>
                      )}
                    </div>

                    <div className="version-actions">
                      {!version.is_current &&
                        version.available && (
                          <button
                            type="button"
                            className="version-restore-button"
                            onClick={() =>
                              setSelectedVersion(
                                version
                              )
                            }
                            disabled={
                              rollingBack
                            }
                          >
                            Khôi phục
                          </button>
                        )}

                      {!version.available && (
                        <span className="version-disabled">
                          Không khả dụng
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
        </div>

        <div className="version-modal-footer">
          <button
            type="button"
            className="version-cancel-button"
            onClick={onClose}
            disabled={rollingBack}
          >
            Đóng
          </button>
        </div>

        {/* Confirmation */}
        {selectedVersion && !rollingBack && (
          <div className="rollback-confirm-overlay">
            <div className="rollback-confirm-modal">
              <div className="rollback-icon">
                ↶
              </div>

              <h4>
                Khôi phục phiên bản?
              </h4>

              <p>
                Bạn có chắc muốn khôi phục{" "}
                <strong>
                  Version{" "}
                  {
                    selectedVersion.version_number
                  }
                </strong>{" "}
                của tài liệu này?
              </p>

              <p className="rollback-warning">
                Sau khi khôi phục, hệ thống sẽ
                re-index vector để chatbot sử
                dụng phiên bản này.
              </p>

              <div className="rollback-actions">
                <button
                  type="button"
                  className="rollback-cancel"
                  onClick={() =>
                    setSelectedVersion(null)
                  }
                >
                  Hủy
                </button>

                <button
                  type="button"
                  className="rollback-confirm"
                  onClick={() =>
                    void handleRollback()
                  }
                >
                  Khôi phục
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Re-index progress */}
        {rollingBack && (
          <div className="rollback-confirm-overlay">
            <div className="rollback-progress-modal">
              <div className="rollback-spinner" />

              <h4>
                Đang khôi phục phiên bản...
              </h4>

              <p>
                Hệ thống đang cập nhật phiên bản
                và re-index vector.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VersionHistoryModal;