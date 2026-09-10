# Test doc_processing

## Test All in one trong Docker

1. Đặt file `.pdf`, `.docx` hoặc `.txt` vào:

   ```
   backend/documents/test/
   ```

2. Khởi động Docker:

   ```
   docker compose up --build
   ```

   Nếu vừa sửa code, dùng docker compose up --build.

3. Chạy test ingestion:

   ```
   docker compose exec app python -m app.doc_processing.test_ingestion --owner-id (replace with number)
   E.g: docker compose exec app python -m app.doc_processing.test_ingestion --owner-id 3
   ```

4. Kiểm tra kết quả trong:

   ```
   backend/app/doc_processing/doc/pipeline_status.json
   backend/app/doc_processing/doc/chunks.json
   ```

## Test từng file

### 1. `parsing.py`

Đọc file và tạo parsed blocks, không cần DB và không ghi `chunks.json`:

```powershell
docker compose exec app python -c "from app.doc_processing.parsing import parse_document; blocks=parse_document('/app/backend/documents/test/example.docx', 'example.docx', 999); print('blocks=', len(blocks)); print(blocks[0] if blocks else 'EMPTY')"
```

Kết quả cần có `blocks > 0`, mỗi block gồm `document_id`, `page`, `text`.

### 2. `chunking.py`

Chunk parsed blocks trong bộ nhớ, không cần DB và không ghi file:

```powershell
docker compose exec app python -c "from app.doc_processing.parsing import parse_document; from app.doc_processing.chunking import chunk_blocks; blocks=parse_document('/app/backend/documents/test/example.docx', 'example.docx', 999); chunks=chunk_blocks(blocks); print('blocks=', len(blocks), 'chunks=', len(chunks)); print(chunks[0] if chunks else 'EMPTY')"
```

Chạy riêng module chỉ kiểm tra entrypoint:

```powershell
docker compose exec app python -m app.doc_processing.chunking
```

Kết quả gồm số chunk demo trong bộ nhớ và `total_chunks_in_store`, là tổng số chunk đang có trong `chunks.json`. Demo không ghi thêm dữ liệu vào kho.

### 3. `ingestion.py`

`ingestion.py` cần record tài liệu trong PostgreSQL, nên không test bằng cách chạy file trực tiếp. Chạy file trực tiếp chỉ in hướng dẫn:

```powershell
docker compose exec app python -m app.doc_processing.ingestion
```

Để test ingestion thật, dùng bước `test_ingestion.py` bên dưới.

### 4. `pipeline.py`

`pipeline.py` cũng cần `document_id` có trong PostgreSQL. Chạy file trực tiếp không xử lý tài liệu:

```powershell
docker compose exec app python -m app.doc_processing.pipeline
```

Pipeline thật được gọi tự động bởi `test_ingestion.py` hoặc API upload.

### 5. `test_ingestion.py`

Đây là lệnh test đầy đủ cho file trong `backend/documents/test`:

```powershell
docker compose exec app python -m app.doc_processing.test_ingestion --owner-id (replace with number)
E.g: docker compose exec app python -m app.doc_processing.test_ingestion --owner-id 3
```

Luồng thực tế:

```text
test_ingestion -> pipeline -> ingestion -> parsing -> chunking
```

Tool tạo record trong PostgreSQL Docker, giữ nguyên file test, rồi ingest, parse và chunk. Chạy lại cùng file sẽ báo `SKIP` nếu file đã có record.

## Kiểm tra kết quả

Kết quả thành công:

```
example.docx: document_id=# status=chunked chunks=#
total_chunks_in_store=#
```

Kiểm tra trạng thái tại:

```
backend/app/doc_processing/doc/pipeline_status.json
```

Kiểm tra chunk tại:

```
backend/app/doc_processing/doc/chunks.json
```

`status=chunked` nghĩa là pipeline đã parse và chunk thành công. `chunk_count` là số chunk của tài liệu.
`total_chunks_in_store` là tổng số chunk của tất cả tài liệu hiện có trong `chunks.json`.