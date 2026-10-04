import uuid

class MinioStorageService:
    def __init__(self):
        self.bucket_name = "documents"

    def create_multipart_upload(self, object_key: str, content_type: str = "application/octet-stream") -> str:
        # Giả lập trả về UploadId từ MinIO
        return f"mock_upload_{uuid.uuid4().hex[:16]}"

    def upload_part(self, object_key: str, upload_id: str, part_number: int, data: bytes) -> str:
        # Giả lập trả về ETag chuẩn định dạng S3 (có dấu nháy kép bọc ngoài)
        return f'"{uuid.uuid4().hex[:16]}"'

    def complete_multipart_upload(self, object_key: str, upload_id: str, parts: list):
        # Giả lập hoàn tất gom các chunk
        return {
            "Bucket": self.bucket_name,
            "Key": object_key,
            "ETag": f'"{uuid.uuid4().hex[:16]}"',
        }

    def abort_multipart_upload(self, object_key: str, upload_id: str):
        return {}


storage_service = MinioStorageService()