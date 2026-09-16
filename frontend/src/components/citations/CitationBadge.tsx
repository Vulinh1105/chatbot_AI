import React from 'react';
import type { Citation } from '../../types/chat';
import './Citations.css';

interface CitationBadgeProps {
  citationId: number;
  citation?: Citation;
  isActive?: boolean;
  onClick: (citation: Citation) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citationId,
  citation,
  isActive = false,
  onClick,
}) => {
  const tooltipText = citation
    ? `Tài liệu: ${citation.document_title}${citation.page_number ? ` (Trang ${citation.page_number})` : ''} — Bấm để mở văn bản gốc`
    : `Trích dẫn [${citationId}]`;

  return (
    <button
      type="button"
      onClick={() => citation && onClick(citation)}
      disabled={!citation}
      aria-label={tooltipText}
      title={tooltipText}
      className={`citation-badge-btn ${isActive ? 'active' : ''}`}
    >
      [{citationId}]
    </button>
  );
};
