import React, { useEffect, useState } from 'react';
import type { Citation } from '../../types/chat';

interface SourceDrawerProps {
  citation: Citation | null;
  onClose: () => void;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({ citation, onClose }) => {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (citation) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [citation, onClose]);

  if (!citation) return null;

  const handleCopySnippet = () => {
    if (!citation.snippet) return;
    navigator.clipboard.writeText(citation.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isPdf = citation.document_title.toLowerCase().endsWith('.pdf');
  const icon = isPdf ? '📕' : '📘';

  return (
    <div className={`source-drawer-overlay ${citation ? 'open' : ''}`} onClick={onClose}>
      <aside
        className="source-drawer-panel"
        onClick={(e) => e.stopPropagation()}
        aria-label="Chi tiết tài liệu trích dẫn"
      >
        {/* Header */}
        <div className="source-drawer-header">
          <div className="source-drawer-header-left">
            <span className="source-drawer-icon">{icon}</span>
            <div style={{ overflow: 'hidden' }}>
              <h3 className="source-drawer-header-title" title={citation.document_title}>
                {citation.document_title}
              </h3>
              <p className="source-drawer-meta">
                Trang: <strong>{citation.page_number}</strong>
                {citation.score !== undefined && ` • Độ khớp: ${(citation.score * 100).toFixed(0)}%`}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="source-drawer-close-btn"
            title="Đóng (ESC)"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="source-drawer-body">
          <div className="source-drawer-section-title">
            <span>ĐOẠN TRÍCH DẪN NGUYÊN VĂN</span>
            <button
              type="button"
              onClick={handleCopySnippet}
              className="source-drawer-copy-btn"
            >
              {copied ? '✓ Đã chép' : '📋 Sao chép'}
            </button>
          </div>

          <div className="source-drawer-snippet-box">
            {citation.snippet}
          </div>
        </div>

        {/* Footer */}
        <div className="source-drawer-footer">
          {citation.file_url ? (
            <a
              href={`${citation.file_url}#page=${citation.page_number}`}
              target="_blank"
              rel="noopener noreferrer"
              className="source-drawer-btn source-drawer-btn-primary"
              style={{ textDecoration: 'none' }}
            >
              📖 Mở trang {citation.page_number} gốc
            </a>
          ) : (
            <button
              type="button"
              onClick={onClose}
              className="source-drawer-btn source-drawer-btn-primary"
            >
              Đã hiểu
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="source-drawer-btn source-drawer-btn-secondary"
          >
            Đóng
          </button>
        </div>
      </aside>
    </div>
  );
};
