# Kiểm tra UI chat local

Trạng thái: chưa kiểm tra bằng trình duyệt (công cụ không có browser kết nối).
Build/lint và 16 test store/service pass; các kết quả đó không chứng minh layout/focus đúng.

Chạy `npm.cmd run dev` tại frontend, mở URL Vite in trong terminal. Đăng nhập
demo@docbot.local / 123456. Kiểm tra lần lượt desktop, 768px, 375px và 320px.

| Ca kiểm tra | Kết quả mong đợi | Trạng thái |
| --- | --- | --- |
| Header/sidebar | Không tràn ngang; điều hướng có tên khi dùng trình đọc màn hình; focus rõ | Chưa chạy |
| Chat mới | Các hàng hội thoại cách nhau, nút xóa không đè tiêu đề; empty state cách input | Chưa chạy |
| Nhập tiếng Việt | Enter gửi; Shift+Enter xuống dòng; IME không gửi nhầm; giữ Enter không gửi trùng | Chưa chạy |
| Textarea | 3–6 dòng rồi cuộn; xóa/gửi thu nhỏ; đổi chiều rộng tính lại chiều cao | Chưa chạy |
| Kết thúc gửi | Nếu focus đã mất khỏi input khi khóa, trả về input; không giành focus đang ở điều khiển khác | Chưa chạy |
| Streaming | Tin user hiện ngay; assistant tăng dần; không thêm nhiều bubble cho cùng lượt | Chưa chạy |
| Đọc phía trên | Gửi vài lượt rồi cuộn lên khi stream; không tự kéo xuống; nút Xuống cuối hoạt động | Chưa chạy |
| Markdown/code dài | Văn bản xuống dòng; code cuộn trong block; trang không tràn ngang | Chưa chạy |
| Dừng | [slow] rồi Dừng trước phần đầu; Dừng giữa stream giữ nội dung và cho gửi mới | Chưa chạy |
| Retry | [error] và [stream-error]; retry không nhân đôi câu hỏi, thay phần trả lời lỗi | Chưa chạy |
| Chuyển hội thoại | Hai draft/lịch sử riêng; stream về đúng hội thoại ban đầu | Chưa chạy |
| Xóa | Xóa active chọn hội thoại còn lại; xóa cuối tạo mới; xóa pending không hồi sinh dữ liệu | Chưa chạy |
| Mobile | Hội thoại mở/đóng bằng bàn phím; chọn/xóa trả focus về nút mở; Dừng không bị ép/tràn | Chưa chạy |
| Cleanup | Rời /chat hủy; đăng xuất xóa history/draft; reload về hội thoại trống | Chưa chạy |

Khi có lỗi, ghi chiều rộng cửa sổ, thao tác tái hiện, kết quả mong đợi/thực tế
và ảnh đúng vùng lỗi. Không đánh dấu pass khi mới chỉ đọc CSS hoặc chạy unit tests.
