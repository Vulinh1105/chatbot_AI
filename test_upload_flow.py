import os
import httpx

# Gọi trực tiếp qua localhost bên trong container
BASE_URL = "http://127.0.0.1:8000/api/v1"

# Thay thông tin tài khoản test nếu cần
USERNAME = "ducanhlcxyz1"
PASSWORD = "ducanhlcxyz1"


def run_test():
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        print("1. Đăng nhập để lấy Access Token...")
        login_res = client.post(
            "/auth/login",
            data={"username": USERNAME, "password": PASSWORD},
        )
        if login_res.status_code != 200:
            print(f"[-] Đăng nhập thất bại: {login_res.status_code} - {login_res.text}")
            return

        token = login_res.json().get("access_token")
        client.headers.update({"Authorization": f"Bearer {token}"})
        print("[+] Đăng nhập thành công!")

        # Tạo file mẫu 12 MiB để test cắt 2 chunk (mỗi chunk 6 MiB)
        test_filename = "/tmp/test_document.bin"
        file_size = 12 * 1024 * 1024  # 12 MiB
        chunk_size = 6 * 1024 * 1024  # 6 MiB

        print(f"\n2. Tạo file mẫu '{test_filename}' dung lượng {file_size // (1024*1024)} MiB...")
        with open(test_filename, "wb") as f:
            f.write(os.urandom(file_size))

        try:
            print("\n3. Khởi tạo phiên Multipart Upload (/upload/init)...")
            init_payload = {
                "filename": "test_document.bin",
                "total_size_bytes": file_size,
                "chunk_size_bytes": chunk_size,
                "content_type": "application/octet-stream",
            }
            init_res = client.post("/documents/upload/init", json=init_payload)
            if init_res.status_code != 200:
                print(f"[-] Init upload thất bại: {init_res.status_code} - {init_res.text}")
                return

            session_data = init_res.json()
            session_id = session_data["session_id"]
            total_parts = session_data["total_parts"]
            print(f"[+] Phiên upload tạo thành công: session_id={session_id}, total_parts={total_parts}")

            print("\n4. Đang tải từng part lên MinIO...")
            with open(test_filename, "rb") as f:
                for part_num in range(1, total_parts + 1):
                    chunk = f.read(chunk_size)
                    files = {"file": (f"part_{part_num}", chunk, "application/octet-stream")}
                    data = {"part_number": part_num}
                    part_res = client.post(
                        f"/documents/upload/{session_id}/part",
                        files=files,
                        data=data,
                    )
                    if part_res.status_code != 200:
                        print(f"[-] Upload part {part_num} thất bại: {part_res.status_code} - {part_res.text}")
                        return
                    print(f"[+] Đã upload thành công Part {part_num}/{total_parts} (ETag: {part_res.json().get('etag')})")

            print("\n5. Kiểm tra trạng thái phiên upload (/upload/{session_id}/status)...")
            status_res = client.get(f"/documents/upload/{session_id}/status")
            print(f"[+] Status phiên upload: {status_res.json()}")

            print("\n6. Gọi Complete Upload (/upload/{session_id}/complete)...")
            complete_res = client.post(f"/documents/upload/{session_id}/complete")
            if complete_res.status_code != 200:
                print(f"[-] Complete upload thất bại: {complete_res.status_code} - {complete_res.text}")
                return

            complete_data = complete_res.json()
            document_id = complete_data["document_id"]
            print(f"[+] Hoàn tất multipart upload! Document ID: {document_id}, Version: {complete_data['version_number']}")

            print(f"\n7. Lấy chi tiết tài liệu ID {document_id}...")
            doc_res = client.get(f"/documents/{document_id}")
            print(f"[+] Document Details: {doc_res.json()}")

            print("\n===> TẤT CẢ CÁC BƯỚC TEST MULTIPART UPLOAD ĐÃ HOÀN TẤT THÀNH CÔNG! <===")

        finally:
            if os.path.exists(test_filename):
                os.remove(test_filename)


if __name__ == "__main__":
    run_test()