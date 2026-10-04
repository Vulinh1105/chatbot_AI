from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv()

COLLECTION_NAME = "chatbot_documents_v2"

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

info = client.get_collection(COLLECTION_NAME)

print("=" * 80)
print("COLLECTION INFO")
print("=" * 80)

print(f"Collection : {COLLECTION_NAME}")
print(f"Points     : {info.points_count}")
print(f"Status     : {info.status}")

points, next_page = client.scroll(
    collection_name=COLLECTION_NAME,
    limit=3,
    with_payload=True,
    with_vectors=True,
)

print("\n" + "=" * 80)
print("DATA + VECTOR")
print("=" * 80)

for i, point in enumerate(points, start=1):

    print(f"\n--- POINT {i} ---")

    print("ID:")
    print(point.id)

    print("\nPAYLOAD:")
    print(point.payload)

    print("\nVECTOR:")

    if point.vector is None:
        print("❌ Không có vector")

    elif isinstance(point.vector, dict):
        for name, vector in point.vector.items():
            print(
                f"{name}: dimension = {len(vector)}"
            )
            print(
                f"first 5 values = {vector[:5]}"
            )

    else:
        print(
            f"dimension = {len(point.vector)}"
        )
        print(
            f"first 5 values = {point.vector[:5]}"
        )