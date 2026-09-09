# ThinkDocu API

Backend REST API cho ThinkDocu, hiện cung cấp xác thực JWT và quản lý người dùng. Ứng dụng được xây dựng bằng FastAPI, SQLAlchemy bất đồng bộ và PostgreSQL hoặc SQLite.

## Chức năng hiện có

- Đăng ký tài khoản với username và email duy nhất.
- Đăng nhập bằng form OAuth2 hoặc JSON, nhận JWT access token.
- Xem, cập nhật và xóa hồ sơ của người dùng đang đăng nhập.
- Quản trị viên có thể xem, tạo, sửa và xóa mọi tài khoản.
- Người dùng có thể tạo, xem, sửa và xóa các đoạn chat của mình; admin có toàn quyền với mọi đoạn chat.
- Kiểm tra trạng thái kết nối cơ sở dữ liệu.
- Swagger UI tự sinh tại `/docs`.

## Công nghệ

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2 (async) và Alembic
- PostgreSQL + `asyncpg`; SQLite + `aiosqlite` cho chạy nhanh cục bộ
- JWT (PyJWT), bcrypt và Pydantic v2
- Docker Compose

## Cấu trúc thư mục

```text
└── backend              
    ├── alembic/
    └── app/
        ├── ai_agent/            # 
        ├── api/                 # Router và dependency xác thực
        ├── core/                # Cấu hình, security...
        ├── doc_processing/      #
        ├── model/               # SQLAlchemy models
        ├── repository/          # Truy cập dữ liệu
        ├── schemas/             # Request/response schemas
        ├── services/            # JWT và mã hóa mật khẩu
        ├── alembic/             # Database migrations
        ├── database.py          # Async engine và database session
        ├── main.py              # Khởi tạo FastAPI
        ├── data/                # Khởi tạo FastAPI
        └── documents/           # Lưu trữ tài liệu up lên
            ├── 1/               # Lưu trữ tài liệu theo user_id
            └── 2/               # Lưu trữ tài liệu user_id
    └── tests/
        └── test_api.py          # Kiểm thử luồng xác thực và người dùng
```

## Yêu cầu

- Python 3.12+ nếu chạy trực tiếp trên máy
- Docker Desktop nếu chạy bằng Docker Compose

## Cấu hình môi trường

Tạo file `.env` ở thư mục gốc dự án. Ví dụ:

```env
API_V1_STR=/api/v1
PROJECT_NAME=ThinkDocu
SECRET_KEY=thay-bang-mot-chuoi-ngau-nhien-dai-va-bao-mat
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ADMIN_USERNAME=admin
DOCUMENTS_DIR=./backend/documents
```

### Chạy toàn bộ ứng dụng bằng Docker Compose

Khi API và PostgreSQL cùng chạy trong Docker Compose, dùng hostname `db` (tên service), không dùng `localhost`:

```env
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://thinkdocu:thinkdocu_password@db:5432/thinkdocu_db
```

`postgresql+asyncpg` được khuyến nghị vì ứng dụng sử dụng SQLAlchemy bất đồng bộ.

### Chạy API trực tiếp trên máy, PostgreSQL chạy bằng Docker

Khi Uvicorn chạy từ terminal hoặc IDE trên máy, dùng `localhost` vì cổng PostgreSQL đã được Docker map ra máy host:

```env
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://thinkdocu:thinkdocu_password@localhost:5432/thinkdocu_db
```

> Code vẫn tự chuyển URL bắt đầu bằng `postgresql://` sang `postgresql+asyncpg://`, nhưng nên ghi rõ `+asyncpg` để cấu hình dễ hiểu và nhất quán.

### Chạy nhanh với SQLite

Nếu không cấu hình `SQLALCHEMY_DATABASE_URI`, ứng dụng mặc định dùng:

```env
SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:///./thinkdocu.db
```

## Chạy bằng Docker Compose

```bash
docker compose up --build
```

API chạy tại [http://localhost:8000](http://localhost:8000), tài liệu Swagger tại [http://localhost:8000/docs](http://localhost:8000/docs). Docker Compose tự chạy migration Alembic trước khi khởi động API.

Dừng các container:

```bash
docker compose down
```

## Chạy trực tiếp trên máy

```bash
python -m venv .venv
```

Kích hoạt môi trường ảo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cài dependencies và chạy migration:

```bash
pip install -r requirements.txt
alembic upgrade head
```

Khởi động development server:

```bash
uvicorn --app-dir backend app.main:app --reload
```

## API chính

| Method | Endpoint | Mô tả | Xác thực |
| --- | --- | --- | --- |
| `GET` | `/` | Thông tin API | Không |
| `GET` | `/db-check` | Kiểm tra database | Không |
| `POST` | `/api/v1/auth/register` | Đăng ký tài khoản | Không |
| `POST` | `/api/v1/auth/login` | Đăng nhập bằng form OAuth2 | Không |
| `POST` | `/api/v1/auth/login/json` | Đăng nhập bằng JSON | Không |
| `GET` | `/api/v1/users/me` | Xem hồ sơ hiện tại | JWT |
| `PUT` | `/api/v1/users/me` | Cập nhật hồ sơ hiện tại | JWT |
| `DELETE` | `/api/v1/users/me` | Xóa tài khoản hiện tại | JWT |
| `GET` | `/api/v1/users/` | Danh sách người dùng | Admin |
| `POST` | `/api/v1/users/` | Tạo người dùng | Admin |
| `GET` | `/api/v1/users/{user_id}` | Xem người dùng theo ID | Admin |
| `PUT` | `/api/v1/users/{user_id}` | Cập nhật người dùng | Admin |
| `DELETE` | `/api/v1/users/{user_id}` | Xóa người dùng | Admin |
| `POST` | `/api/v1/chats/` | Tạo đoạn chat | JWT |
| `GET` | `/api/v1/chats/` | Xem các đoạn chat được phép truy cập | JWT |
| `GET` | `/api/v1/chats/{chat_id}` | Xem một đoạn chat | JWT |
| `PUT` | `/api/v1/chats/{chat_id}` | Sửa tiêu đề đoạn chat | JWT |
| `DELETE` | `/api/v1/chats/{chat_id}` | Xóa đoạn chat | JWT |
| `POST` | `/api/v1/documents/upload` | Upload file multipart | JWT |
| `GET` | `/api/v1/documents/` | Danh sách file của mình (admin: tất cả) | JWT |
| `GET` | `/api/v1/documents/{document_id}` | Metadata của file | Chủ sở hữu/Admin |
| `GET` | `/api/v1/documents/{document_id}/download` | Đọc/tải file gốc | Chủ sở hữu/Admin |
| `PUT` | `/api/v1/documents/{document_id}` | Thay thế nội dung file bằng multipart `file` | Chủ sở hữu/Admin |
| `DELETE` | `/api/v1/documents/{document_id}` | Xóa file | Chủ sở hữu/Admin |
Quyền admin được cấp cho người dùng đầu tiên đăng ký (`id = 1`) hoặc người có `username` trùng với `ADMIN_USERNAME` (không phân biệt hoa/thường).

## Quản lý tài liệu

File upload được lưu nguyên byte vào thư mục cấu hình `DOCUMENTS_DIR` (mặc định là `backend/documents/` ở thư mục dự án), theo cấu trúc `{owner_id}/{document_id}`. Đường dẫn tương đối luôn được tính từ thư mục gốc dự án, không phụ thuộc vào thư mục dùng để khởi động Uvicorn. Docker Compose mount trực tiếp thư mục này vào container để file vẫn còn sau khi container được tạo lại. Tên file gốc, MIME type, dung lượng và chủ sở hữu được lưu trong database.

Người dùng thường chỉ có thể liệt kê, xem metadata, tải xuống, thay thế và xóa file của chính họ. Nếu truy cập ID của người khác, API trả `404`. Admin có thể thực hiện các thao tác quản lý với mọi file. Xóa tài khoản cũng dọn metadata và file của tài khoản đó.


## Kiểm thử

```bash
pytest -q
```
