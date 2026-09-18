from __future__ import annotations

from langchain_core.documents import Document

from .evidence import judge_evidence


# TEST CASES
TEST_CASES = [
    {
        "name": "CASE 1 - China vs Vietnam",
        "query": "Trung Quốc tăng trưởng GDP quý II năm 2025 là bao nhiêu?",
        "chunks": [
            Document(
                page_content=(
                    "Tăng trưởng GDP của Trung Quốc năm 2025 theo quý: "
                    "Q1 đạt 5,4%, Q2 đạt 5,2%, Q3 đạt 4,8%, "
                    "Q4 đạt 4,5%."
                ),
                metadata={
                    "document_id": 54,
                    "source": "China_2025.docx",
                    "page": 2,
                    "chunk_id": "doc54_p2_c001_semantic",
                },
            ),
            Document(
                page_content=(
                    "Tăng trưởng GDP của Việt Nam năm 2025 theo quý: "
                    "Q1 đạt 7,05%, Q2 đạt 8,16%, Q3 đạt 8,25%, "
                    "Q4 đạt 8,46%."
                ),
                metadata={
                    "document_id": 55,
                    "source": "Vietnam_2025.docx",
                    "page": 1,
                    "chunk_id": "doc55_p1_c002_semantic",
                },
            ),
        ],
    },
    {
        "name": "CASE 2 - Alibaba marketing",
        "query": "Chiến lược marketing của Alibaba là gì?",
        "chunks": [
            Document(
                page_content=(
                    "Chiến lược kinh doanh của Alibaba tập trung "
                    "tạo ra một hệ sinh thái, dẫn dắt các doanh nghiệp, "
                    "nhà cung cấp và người tiêu dùng đến với nhau."
                ),
                metadata={
                    "document_id": 56,
                    "source": "ali33.docx",
                    "page": 4,
                    "chunk_id": "doc56_p4_c004_semantic",
                },
            ),
            Document(
                page_content=(
                    "Alibaba hướng đến hai giá trị cốt lõi: "
                    "sự sáng tạo và con người."
                ),
                metadata={
                    "document_id": 56,
                    "source": "ali33.docx",
                    "page": 3,
                    "chunk_id": "doc56_p3_c003_semantic",
                },
            ),
        ],
    },
    {
        "name": "CASE 3 - Alibaba core values",
        "query": "Alibaba hướng đến những giá trị cốt lõi nào?",
        "chunks": [
            Document(
                page_content=(
                    "Chiến lược kinh doanh. "
                    "Hướng đến hai giá trị cốt lõi: "
                    "sự sáng tạo và con người."
                ),
                metadata={
                    "document_id": 56,
                    "source": "ali33.docx",
                    "page": 3,
                    "chunk_id": "doc56_p3_c003_semantic",
                },
            ),
        ],
    },
]


def print_case_result(
    case_name: str,
    query: str,
    chunks: list[Document],
) -> None:

    print("\n" + "=" * 80)
    print(case_name)
    print("=" * 80)

    print("\nQUERY:")
    print(query)

    print("\nCANDIDATE CHUNKS:")

    for index, document in enumerate(chunks):

        print(f"\n[{index}]")
        print("SOURCE:", document.metadata.get("source"))
        print("PAGE:", document.metadata.get("page"))
        print("CHUNK ID:", document.metadata.get("chunk_id"))
        print("CONTENT:")
        print(document.page_content)

    print("\nCALLING EVIDENCE JUDGE...")

    result = judge_evidence(
        query,
        chunks,
    )

    print("\nEVIDENCE JUDGE RESULT:")
    print("sufficient:", result.sufficient)
    print("supported_indices:", result.supported_indices)
    print("reason:", result.reason)

    print("\nSELECTED EVIDENCE:")

    if not result.supported_indices:
        print("❌ Không có evidence được chọn.")

    for index in result.supported_indices:

        if 0 <= index < len(chunks):

            document = chunks[index]

            print(f"\n[{index}]")
            print("SOURCE:", document.metadata.get("source"))
            print("PAGE:", document.metadata.get("page"))
            print("CHUNK ID:", document.metadata.get("chunk_id"))
            print("CONTENT:")
            print(document.page_content)


def main() -> None:

    print("=" * 80)
    print("EVIDENCE SELECTION TEST")
    print("=" * 80)

    for case in TEST_CASES:

        print_case_result(
            case["name"],
            case["query"],
            case["chunks"],
        )

    print("\n" + "=" * 80)
    print("TEST FINISHED")
    print("=" * 80)


if __name__ == "__main__":
    main()