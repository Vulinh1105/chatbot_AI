import React from 'react';
import { Citation } from '../../types/chat';

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
    ? `Nguồn: ${citation.document_title}${citation.page_number ? ` (Trang ${citation.page_number})` : ''}`
    : `Trích dẫn [${citationId}]`;

  return (
    <button
      type="button"
      onClick={() => citation && onClick(citation)}
      disabled={!citation}
      aria-label={tooltipText}
      title={tooltipText}
      className={`inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-xs font-semibold rounded transition-all duration-200 shadow-sm align-baseline cursor-pointer ${
        isActive
          ? 'bg-indigo-600 text-white border border-indigo-700 ring-2 ring-indigo-200 scale-105'
          : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 hover:text-indigo-900 border border-indigo-200 hover:scale-105'
      } ${!citation ? 'opacity-60 cursor-not-allowed' : ''}`}
    >
      <span className="font-mono text-[11px] leading-none">[{citationId}]</span>
    </button>
  );
};
