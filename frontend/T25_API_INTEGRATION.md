# T25: tích hợp API chat

## Chạy frontend

`npm ci`, sau đó `npm run dev` trong thư mục frontend.
`VITE_API_URL` là địa chỉ gốc backend, không kèm `/api/v1`.
Service dùng Axios trong `src/services/api.ts`, tự gắn accessToken hiện có.

## Luồng đã nối

- Tạo chat trên backend khi gửi câu hỏi đầu tiên, dùng ID backend cho mọi request.
- Gửi POST `/api/v1/chats/{id}/ask` với `{question}`; chờ JSON hoàn chỉnh.
- Tải danh sách và toàn bộ các trang lịch sử theo `next_cursor` / `has_more`.
- Xóa trên backend thành công mới xóa khỏi giao diện.
- Hiển thị nguồn `{source, pages}` dạng văn bản; chưa có dữ liệu để liên kết trang tài liệu.
- Dừng chờ hủy request phía trình duyệt. Backend có thể tiếp tục xử lý.
- Khi lỗi mạng hoặc hết thời gian, tải lại lịch sử trước khi gửi lại. Backend chưa có khóa chống trùng request.

## Kiểm tra

`npm test`, `npm run lint`, `npm run build`.
Test dùng service giả lập để kiểm tra hợp đồng API và vòng đời request; không chứng minh RAG trên server hoạt động.

## Điều kiện kiểm thử trên server

Backend phải có POST `/api/v1/chats/{id}/ask` và GET `/api/v1/chats/{id}/messages`.
Tại lần kiểm tra ngày 15/09/2026, staging cấu hình trong frontend chưa công bố hai route này trong OpenAPI; local port 8000 chưa chạy.
Cần BE triển khai API mới, chạy migration chat_messages và cấu hình RAG trước khi kiểm thử end-to-end.
API hiện chưa stream từng token. Session RAG và dữ liệu citation đầy đủ còn cần BE xử lý.
