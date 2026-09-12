# from qdrant_client import QdrantClient
# from dotenv import load_dotenv
# import os
#
# load_dotenv()
#
# QDRANT_URL = os.getenv("QDRANT_URL")
# QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
# COLLECTION_NAME = "chatbot_documents"
#
# print("QDRANT_URL:", QDRANT_URL)
#
# try:
#     client = QdrantClient(
#         url=QDRANT_URL,
#         api_key=QDRANT_API_KEY,
#         timeout=60,
#     )
#
#     # 1. Test kết nối
#     collections = client.get_collections()
#
#     print("\nQdrant connection OK")
#     print("Collections:")
#
#     for collection in collections.collections:
#         print("-", collection.name)
#
#     # 2. Kiểm tra collection
#     info = client.get_collection(COLLECTION_NAME)
#
#     print("\nCollection:", COLLECTION_NAME)
#     print("Status:", info.status)
#     print("Points count:", info.points_count)
#
#     # 3. In cấu hình vector
#     print("\nVectors config:")
#     print(info.config.params.vectors)
#
#     # 4. Đếm chính xác số point hiện tại
#     count_result = client.count(
#         collection_name=COLLECTION_NAME,
#         exact=True,
#     )
#
#     print("\nExact points count:", count_result.count)
#
#     print("\nQdrant test completed successfully.")
#
# except Exception as e:
#     print("\nQdrant test FAILED")
#     print(type(e).__name__)
#     print(str(e))

# from retrieval import db
#
# query = "phương thức thanh toán"
#
# results = db.similarity_search_with_relevance_scores(query, k=10)
#
# print(f"\nFound {len(results)} results:\n")
#
# for i, (doc, score) in enumerate(results, 1):
#     print("=" * 80)
#     print(f"Rank: {i}")
#     print(f"Score: {score}")
#     print(f"Chunk ID: {doc.metadata.get('chunk_id')}")
#     print(f"Document ID: {doc.metadata.get('document_id')}")
#     print(f"Page: {doc.metadata.get('page')}")
#     print("Content:")
#     print(doc.page_content[:500])

from retrieval import retrieve
#
# query = "phương thức thanh toán"
#
# results = retrieve(query)
#
# print(f"\nFound {len(results)} results:\n")
#
# for i, doc in enumerate(results, 1):
#     print("=" * 80)
#     print(f"Rank: {i}")
#     print(f"Chunk ID: {doc.metadata.get('chunk_id')}")
#     print(f"Document ID: {doc.metadata.get('document_id')}")
#     print(f"Page: {doc.metadata.get('page')}")
#     print("Content:")
#     print(doc.page_content[:500])

queries = [
    "phương thức thanh toán",
    "có những phương thức thanh toán nào"
]

for query in queries:
    print("\n" + "#" * 100)
    print("QUERY:", query)

    results = retrieve(query)

    print(f"Found {len(results)} results")

    for i, doc in enumerate(results, 1):
        print("\n" + "=" * 80)
        print(f"Rank: {i}")
        print(f"Chunk ID: {doc.metadata.get('chunk_id')}")
        print(f"Document ID: {doc.metadata.get('document_id')}")
        print(f"Page: {doc.metadata.get('page')}")
        print(doc.page_content[:500])