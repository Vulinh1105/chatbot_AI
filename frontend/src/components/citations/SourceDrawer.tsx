import React, { useEffect, useState } from 'react';
import type { Citation } from '../../types/chat';

interface SourceDrawerProps {
  citation: Citation | null;
  onClose: () => void;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({
  citation,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (citation) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [citation, onClose]);

  if (!citation) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(citation.snippet);
    setCopied(true);

    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };

  const fileLink = citation.file_url
    ? citation.page_number
      ? `${citation.file_url}#page=${citation.page_number}`
      : citation.file_url
    : null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Overlay */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-full sm:w-[440px] bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col transition-transform animate-in slide-in-from-right duration-200">

        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2.5 overflow-hidden">

            {/* Document icon */}
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600 flex-shrink-0">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>

            {/* Document information */}
            <div className="overflow-hidden">
              <h3
                className="font-semibold text-sm text-slate-800 truncate"
                title={citation.document_title}
              >
                {citation.document_title}
              </h3>

              <p className="text-xs text-slate-500">
                {citation.page_number ? (
                  <>
                    Vị trí:{' '}
                    <strong className="text-indigo-600">
                      Trang {citation.page_number}
                    </strong>
                  </>
                ) : (
                  <>Tài liệu nguồn</>
                )}

                {citation.score !== undefined &&
                  ` • Độ khớp ${(citation.score * 100).toFixed(0)}%`}
              </p>
            </div>
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition text-sm"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs">

          {/* Evidence */}
          <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-lg text-amber-900">
            <p className="font-semibold mb-0.5">
              Bằng chứng trích dẫn (Evidence):
            </p>

            <p className="leading-relaxed">
              {citation.page_number ? (
                <>
                  Đoạn trích dưới đây nằm ở{' '}
                  <strong>Trang {citation.page_number}</strong> của tài liệu
                  gốc.
                </>
              ) : (
                <>
                  Đoạn trích được truy hồi từ văn bản gốc làm căn cứ trả lời.
                </>
              )}
            </p>
          </div>

          {/* Snippet */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="font-semibold text-slate-700 uppercase text-[10.5px] tracking-wider">
                Nội dung nguyên văn (Snippet):
              </label>

              <button
                onClick={handleCopy}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium transition"
              >
                {copied
                  ? 'Đã sao chép ✓'
                  : 'Sao chép trích dẫn'}
              </button>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 leading-relaxed whitespace-pre-wrap font-sans text-[11.5px] selection:bg-indigo-100">
              {citation.snippet}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-between items-center">

          {/* Open document */}
          {fileLink ? (
            <a
              href={fileLink}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium transition shadow-sm"
            >
              {citation.page_number
                ? `Mở Trang ${citation.page_number} ↗`
                : 'Mở tài liệu gốc ↗'}
            </a>
          ) : (
            <span className="text-[11px] text-slate-400">
              Tài liệu lưu trữ nội bộ
            </span>
          )}

          {/* Close */}
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs font-medium transition"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};