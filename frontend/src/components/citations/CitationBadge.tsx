import React from 'react';
import { Citation } from '../../types/chat';

interface CitationBadgeProps 
{
  citationId: number;
  citation?: Citation;
  onClick: (citation: Citation) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citationId,
  citation,
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={() => citation && onClick(citation)}
      className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 hover:text-indigo-900 border border-indigo-300 rounded cursor-pointer transition shadow-sm align-baseline hover:scale-105"
      title={
        citation
          ? `Nguồn: ${citation.document_title} (Trang ${citation.page_number})`
          : `Trích dẫn [${citationId}]`
      }
    >
      [{citationId}]
    </button>
  );
};
