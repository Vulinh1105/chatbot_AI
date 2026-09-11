// src/pages/FeedbackAdminDashboard.tsx
import { useEffect, useState } from "react";
import { useFeedbackStore } from "../stores/feedbackStore";
import type { FeedbackFilter } from "../services/feedbackService";

const FILTERS: { value: FeedbackFilter; label: string }[] = [
  { value: "all", label: "Tất cả" },
  { value: "up", label: "Hữu ích" },
  { value: "down", label: "Chưa hữu ích" },
];

export default function FeedbackAdminDashboard() {
  const items = useFeedbackStore((s) => s.adminItems);
  const stats = useFeedbackStore((s) => s.adminStats);
  const loading = useFeedbackStore((s) => s.adminLoading);
  const error = useFeedbackStore((s) => s.adminError);
  const loadAdminFeedback = useFeedbackStore((s) => s.loadAdminFeedback);

  const [filter, setFilter] = useState<FeedbackFilter>("all");

  useEffect(() => {
    loadAdminFeedback(filter);
  }, [filter, loadAdminFeedback]);

  const satisfactionRate =
    stats.total > 0 ? Math.round((stats.upCount / stats.total) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-2xl font-bold text-gray-900">Đánh giá phản hồi</h1>
      <p className="mt-1 text-sm text-gray-500">
        Theo dõi mức độ hài lòng của người dùng với câu trả lời của bot.
      </p>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <StatCard label="Tổng đánh giá" value={stats.total} />
        <StatCard label="Tỷ lệ hài lòng" value={`${satisfactionRate}%`} tone="success" />
        <StatCard label="Chưa hài lòng" value={`${100 - satisfactionRate}%`} tone="danger" />
      </div>

      <div className="mt-6 flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFilter(f.value)}
            className={[
              "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
              filter === f.value
                ? "border-blue-600 bg-blue-600 text-white"
                : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50",
            ].join(" ")}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-gray-200 bg-white">
        {loading && <div className="p-6 text-sm text-gray-500">Đang tải...</div>}
        {error && <div className="p-6 text-sm text-red-500">{error}</div>}

        {!loading && !error && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-gray-500">
                <th className="px-4 py-2.5 font-medium">Câu hỏi</th>
                <th className="px-4 py-2.5 font-medium">Người dùng</th>
                <th className="px-4 py-2.5 font-medium">Thời gian</th>
                <th className="px-4 py-2.5 font-medium">Đánh giá</th>
                <th className="px-4 py-2.5 font-medium">Lý do / ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                    Chưa có phản hồi nào.
                  </td>
                </tr>
              )}
              {items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100 last:border-0">
                  <td className="px-4 py-2.5 text-gray-900">{item.question}</td>
                  <td className="px-4 py-2.5 text-gray-500">{item.userId}</td>
                  <td className="px-4 py-2.5 text-gray-500">
                    {new Date(item.createdAt).toLocaleString("vi-VN")}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={[
                        "rounded-full px-2.5 py-1 text-xs font-medium",
                        item.rating === "up"
                          ? "bg-blue-50 text-blue-600"
                          : "bg-red-50 text-red-600",
                      ].join(" ")}
                    >
                      {item.rating === "up" ? "Hữu ích" : "Chưa hữu ích"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-500">{item.comment || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "success" | "danger";
}) {
  const toneClass =
    tone === "success" ? "text-blue-600" : tone === "danger" ? "text-red-500" : "text-gray-900";
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${toneClass}`}>{value}</p>
    </div>
  );
}
