# TÀI LIỆU VẬN HÀNH MÔI TRƯỜNG STAGING
## 1. Thông số Hệ thống & Port
- **Server IP**: 188.245.107.192
- **Web Frontend**: Port 80 (`http://188.245.107.192:80` hoặc `http://188.245.107.192`)
- **Backend API / Swagger**: Port 8000 (`http://188.245.107.192:8000/docs`)
- **Health Check Endpoint**: Port 8000 (`http://188.245.107.192:8000/health`)
- **Qdrant Dashboard**: Port 6333 (`http://188.245.107.192:6333/dashboard`)
- **Database (PostgreSQL)**: Port 5432 (DB: `thinkdocu_db`, User: `thinkdocu`, Pass: `thinkdocu_password`)
## 2. Quy trình Triển khai (Deployment)
- **Tự động (CD Pipeline)**: Merge PR vào nhánh `main`, GitHub Actions tự động kích hoạt cập nhật.
## 3. Kiểm tra Sức khỏe (Health Check)
- **Trạng thái container**: `docker ps`
- **Probe Backend**: `curl -i http://localhost:8000/health` (hoặc `http://localhost:8000/db-check`)

