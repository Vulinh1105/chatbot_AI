import { useEffect, useState } from "react";
import { useFeedbackStore } from "../stores/feedbackStore";
import type { FeedbackFilter } from "../services/feedbackService";
import "./FeedbackAdminDashboard.css";

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
    <div className="feedback-admin">
      <h1>Đánh giá phản hồi</h1>
      <p>Theo dõi mức độ hài lòng của người dùng với câu trả lời của bot.</p>

      <div className="feedback-admin-stats">
        <StatCard label="Tổng đánh giá" value={stats.total} />
        <StatCard label="Tỷ lệ hài lòng" value={`${satisfactionRate}%`} tone="success" />
        <StatCard label="Chưa hài lòng" value={`${100 - satisfactionRate}%`} tone="danger" />
      </div>

      <div className="feedback-admin-filters">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFilter(f.value)}
            className={`feedback-admin-filter-btn${filter === f.value ? " is-active" : ""}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="feedback-admin-table-wrap">
        {loading && <p className="feedback-admin-note">Đang tải...</p>}
        {error && <p className="feedback-admin-note is-error">{error}</p>}

        {!loading && !error && (
          <table className="feedback-admin-table">
            <thead>
              <tr>
                <th>Câu hỏi</th>
                <th>Người dùng</th>
                <th>Thời gian</th>
                <th>Đánh giá</th>
                <th>Lý do / ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="feedback-admin-empty">
                    Chưa có phản hồi nào.
                  </td>
                </tr>
              )}
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.question}</td>
                  <td>{item.userId}</td>
                  <td>{new Date(item.createdAt).toLocaleString("vi-VN")}</td>
                  <td>
                    <span className={`feedback-admin-badge ${item.rating === "up" ? "is-up" : "is-down"}`}>
                      {item.rating === "up" ? "Hữu ích" : "Chưa hữu ích"}
                    </span>
                  </td>
                  <td>{item.comment || "—"}</td>
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
  return (
    <div className="feedback-admin-stat-card">
      <p className="feedback-admin-stat-label">{label}</p>
      <p className={`feedback-admin-stat-value${tone ? ` is-${tone}` : ""}`}>{value}</p>
    </div>
  );
}
