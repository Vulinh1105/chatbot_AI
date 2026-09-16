import React from 'react';
import type { Citation } from '../../types/chat';

interface SourceCardProps {
  citation: Citation;
  isSelected?: boolean;
  onSelect: (citation: Citation) => void;
}

export const SourceCard: React.FC<SourceCardProps> = ({
  citation,
  isSelected,
  onSelect,
}) => {
  const isPdf = citation.document_title.toLowerCase().endsWith('.pdf');
  const icon = isPdf ? '📕' : '📘';

  return (
    <div
      id={`source-card-${citation.citation_id}`}
      onClick={() => onSelect(citation)}
      className={`source-card-item ${isSelected ? 'selected' : ''}`}
      role="button"
      tabIndex={0}
      title="Bấm để mở xem toàn văn trích dẫn"
    >
      {/* 1. Header: Icon + Số trích dẫn + Tên tài liệu */}
      <div className="source-card-top">
        <div className="source-card-title-group">
          <span className="source-card-badge">{citation.citation_id}</span>
          <span>{icon}</span>
          <h4 className="source-card-title">{citation.document_title}</h4>
        </div>
        <span style={{ fontSize: '11px', color: '#94a3b8' }}>↗</span>
      </div>

      {/* 2. Snippet Preview: Trích đoạn ngắn gọn */}
      <p className="source-card-snippet">
        "{citation.snippet}"
      </p>

      {/* 3. Footer: Số trang & Điểm tin cậy */}
      <div className="source-card-bottom">
        <span className="source-card-page">
          Trang {citation.page_number}
        </span>

        {citation.score !== undefined && (
          <span className="source-card-score">
            ✓ {(citation.score * 100).toFixed(0)}% phù hợp
          </span>
        )}
      </div>
    </div>
  );
};
