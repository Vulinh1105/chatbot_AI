import React from 'react';
import { Citation } from '../../types/chat';

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
  return (
    <div
      id={`source-card-${citation.citation_id}`}
      onClick={() => onSelect(citation)}
      className={`p-3 rounded-xl border text-left cursor-pointer transition-all duration-200 ${
        isSelected
          ? 'bg-indigo-50 border-indigo-500 shadow-md ring-2 ring-indigo-200'
          : 'bg-white hover:bg-slate-50 border-slate-200 hover:border-indigo-300 shadow-sm'
      }`}
    >
      {/* 1. SOURCE: Tên tài liệu */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 overflow-hidden">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-semibold text-[11px] flex items-center justify-center">
            {citation.citation_id}
          </span>
          <svg className="w-3.5 h-3.5 text-indigo-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h4 className="text-xs font-semibold text-slate-800 truncate" title={citation.document_title}>
            {citation.document_title}
          </h4>
        </div>
        <svg className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </div>

      {/* 2. SNIPPET: Đoạn trích dẫn nguyên văn */}
      <p className="text-xs text-slate-600 line-clamp-2 italic mb-2 leading-relaxed bg-slate-50 p-2 rounded border border-slate-100">
        "{citation.snippet}"
      </p>

      {/* 3. PAGE & SCORE: Số trang & Độ khớp */}
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 font-medium text-slate-700">
          Trang: <strong className="text-indigo-700">{citation.page_number}</strong>
        </span>

        {citation.score !== undefined && (
          <span className="text-emerald-600 font-medium">
            Độ khớp: {(citation.score * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
};
