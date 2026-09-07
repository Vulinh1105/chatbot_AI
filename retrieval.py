import chromadb
from pathlib import Path

from app.ai_agent.embeddings import EmbeddingService


class VectorRetriever:
    """
    Quản lý Vector Database và thực hiện Semantic Vector Retrieval.
    """

    def __init__(self, collection_name: str = "documents"):
        """
        Khởi tạo Vector Database.
        """

        # Đường dẫn tới backend/vectorstore
        BASE_DIR = Path(__file__).resolve().parents[2]

        vectorstore_path = BASE_DIR / "vectorstore"

        # Tạo thư mục nếu chưa tồn tại
        vectorstore_path.mkdir(parents=True, exist_ok=True)

        # ChromaDB local persistent
        self.client = chromadb.PersistentClient(
            path=str(vectorstore_path)
        )

        # Tạo collection nếu chưa có
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine"
            }
        )

        # Service tạo embedding
        self.embedding_service = EmbeddingService()

    def add_chunks(
        self,
        chunks: list[str],
        metadatas: list[dict],
        ids: list[str]
    ):
        """
        Lưu các chunks vào Vector Database.
        """

        if not (
            len(chunks) == len(metadatas) == len(ids)
        ):
            raise ValueError(
                "chunks, metadatas và ids phải có cùng số lượng phần tử."
            )

        # Chuyển chunks thành vectors
        embeddings = self.embedding_service.embed_texts(chunks)

        # Lưu vào ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

        print(f"Đã lưu {len(chunks)} chunks vào Vector Database.")

    def search(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None
    ) -> list[dict]:
        """
        Tìm kiếm các chunks có ý nghĩa gần nhất với query.

        Parameters:
        - query: Câu hỏi của người dùng.
        - top_k: Số lượng kết quả cần lấy.
        - metadata_filter: Điều kiện lọc metadata.

        Return:
        - Danh sách các chunks liên quan nhất.
        """

        # Chuyển câu hỏi thành vector
        query_embedding = self.embedding_service.embed_text(query)

        # Truy vấn ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=metadata_filter
        )

        retrieved_results = []

        # Nếu không tìm thấy kết quả
        if not results["ids"] or not results["ids"][0]:
            return retrieved_results

        # Chuyển kết quả thành format dễ sử dụng
        for i in range(len(results["ids"][0])):

            document_id = results["ids"][0][i]

            document = results["documents"][0][i]

            metadata = results["metadatas"][0][i]

            distance = results["distances"][0][i]

            # Vì dùng cosine distance:
            # score càng lớn càng giống
            score = 1 - distance

            retrieved_results.append({
                "id": document_id,
                "chunk": document,
                "score": round(score, 4),
                "metadata": metadata
            })

        return retrieved_results


# Test độc lập
if __name__ == "__main__":

    retriever = VectorRetriever()

    # Dữ liệu test
    chunks = [
        "Python là một ngôn ngữ lập trình phổ biến.",
        "Hà Nội là thủ đô của Việt Nam.",
        "Machine Learning là một lĩnh vực của trí tuệ nhân tạo.",
        "ChromaDB được sử dụng để lưu trữ vector embedding.",
        "RAG kết hợp tìm kiếm thông tin với mô hình ngôn ngữ lớn."
    ]

    metadatas = [
        {
            "source": "python.txt",
            "page": 1
        },
        {
            "source": "geography.txt",
            "page": 1
        },
        {
            "source": "ai.txt",
            "page": 2
        },
        {
            "source": "vector_db.txt",
            "page": 1
        },
        {
            "source": "rag.txt",
            "page": 3
        }
    ]

    ids = [
        "chunk_1",
        "chunk_2",
        "chunk_3",
        "chunk_4",
        "chunk_5"
    ]

    # Lưu dữ liệu
    retriever.add_chunks(
        chunks=chunks,
        metadatas=metadatas,
        ids=ids
    )

    # Câu hỏi
    query = "Vector database dùng để làm gì?"

    # Tìm Top 3
    results = retriever.search(
        query=query,
        top_k=3
    )

    print("\nKẾT QUẢ TÌM KIẾM:\n")

    for result in results:
        print(result)