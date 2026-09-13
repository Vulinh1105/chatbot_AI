from pathlib import Path
from langchain_openai import OpenAIEmbeddings
#from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
import os

load_dotenv()


QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "chatbot_documents_v2"


# print("URL:", QDRANT_URL)
# print("API KEY exists:", QDRANT_API_KEY is not None)


embedder = OpenAIEmbeddings(
    model='text-embedding-3-large'
)

# Khởi tạo Qdrant vector store từ collection đã tồn tại
db = QdrantVectorStore.from_existing_collection(
    embedding=embedder,
    collection_name=COLLECTION_NAME,
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=False
)
# print('connected to QDRANT successfully.')


retriever = db.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)
# print('done topK + score')


# Hàm Retrieval
def retrieve(query):
    results = retriever.invoke(query)
    return results


# if __name__ == '__main__':
#     while True:
#         query = input('Question (type "exit" to quit): ')
#
#         if query == 'exit':
#             print('program exited.')
#             break
#         if not query.strip():
#             continue
#
#
#         results = retrieve(query)
#
#         print(f'\nFind {len(results)} chunks:\n')
#
#         for i, doc in enumerate(results, start=1):
#             print(f'--- Result {i} ---')
#             print('Content:', doc.page_content)
#             print('Metadata:', doc.metadata)
#
# print('retrieval done')

from app.ai_agent.retrieval import retrieve
from app.ai_agent.reranking import Reranker
from app.ai_agent.prompt import generate_answer
from app.ai_agent.validation import validate_answer

RERANK_TOP_K = 3

reranker = Reranker()

def run_pipeline(query: str):
    try:
        retrieved_chunks = retrieve(query)
        reranked_chunks, _ = reranker.rerank(
            query,
            retrieved_chunks,
            top_k=RERANK_TOP_K,
        )
        answer = generate_answer(query, reranked_chunks)
        result = validate_answer(answer, reranked_chunks)
        return result
    except Exception:
        return {
            "valid": False,
            "answer": "Tài liệu hiện tại không đề cập vấn đề này.",
            "citations": [],
        }

