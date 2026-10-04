import React, { useState, useId } from 'react';
import type { Citation } from '../../types/chat';
import { CitationBadge } from './CitationBadge';
import { SourceCard } from './SourceCard';
import { SourceDrawer } from './SourceDrawer';

interface AnswerWithCitationsProps {
  content: string;
  citations?: Citation[];
}

export const AnswerWithCitations: React.FC<AnswerWithCitationsProps> = ({
  content,
  citations = [],
}) => {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [hoveredCitationId, setHoveredCitationId] = useState<number | null>(null);
  const instanceId = useId();

  const handleSelectCitation = (citation: Citation) => {
    setSelectedCitation(citation);

    const targetId = `source-card-${instanceId}-${citation.citation_id}`;
    const el = document.getElementById(targetId);

    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      el.classList.add('selected');
      setTimeout(() => {
        el.classList.remove('selected');
      }, 1500);
    }
  };

  const parts = content.split(/(\[\[?\d+\]?\])/g);

  return (
    <div className="answer-citations-container">
      {/* 1. Phần nội dung câu trả lời kèm huy hiệu [1], [2] */}
      <div className="answer-citations-text">
        {parts.map((part, idx) => {
          const match = part.match(/\[\[?(\d+)\]?\]/);
          if (match) {
            const citeId = parseInt(match[1], 10);
            const cite = citations.find((c) => c.citation_id === citeId);
            const isHovered = hoveredCitationId === citeId;

            return (
              <span
                key={idx}
                style={{
                  display: 'inline-block',
                  transition: 'all 0.2s',
                  transform: isHovered ? 'scale(1.15)' : 'none',
                }}
              >
                <CitationBadge
                  citationId={citeId}
                  citation={cite}
                  isActive={selectedCitation?.citation_id === citeId}
                  onClick={handleSelectCitation}
                />
              </span>
            );
          }
          return <span key={idx}>{part}</span>;
        })}
      </div>

      {/* 2. Phần chân trang: Khối Card danh sách tài liệu tham khảo */}
      {citations.length > 0 && (
        <div className="citations-footer">
          <div className="citations-footer-header">
            <h5 className="citations-title">
              <span>📚 Nguồn tài liệu tham chiếu ({citations.length}):</span>
            </h5>
            <span className="citations-hint">
              Bấm vào thẻ để xem chi tiết văn bản gốc
            </span>
          </div>

          <div className="source-cards-grid">
            {citations.map((c) => (
              <div
                key={c.citation_id}
                id={`source-card-${instanceId}-${c.citation_id}`}
                onMouseEnter={() => setHoveredCitationId(c.citation_id)}
                onMouseLeave={() => setHoveredCitationId(null)}
              >
                <SourceCard
                  citation={c}
                  isSelected={selectedCitation?.citation_id === c.citation_id}
                  onSelect={handleSelectCitation}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Ngăn kéo trượt xem chi tiết văn bản gốc */}
      <SourceDrawer
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
};
