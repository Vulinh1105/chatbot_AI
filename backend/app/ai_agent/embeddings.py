
from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain_community.vectorstores.utils import DistanceStrategy
from pathlib import Path
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
import os
import json
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

# DATA_PATH='../data'
DATA_PATH = Path(__file__).resolve().parent.parent / 'doc_processing' / 'doc'

# qdrant config
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_KEY')
COLLECTION_NAME = 'chatbot_documents'

def create_vector_db(docs):

    # embedding
    embeddings = OpenAIEmbeddings(
        model='text-embedding-3-large'
    )

    print('Creating embeddings')
    qdrant = QdrantVectorStore.from_documents(
        documents=docs,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
    )

    print('Qdrant created successfully.')

    return qdrant

if __name__ == '__main__':
    # read json
    json_path = DATA_PATH / 'chunks.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    # json -> doc
    docs = [
        Document(
            page_content=chunk['content'],
            metadata={
                'chunk_id': chunk['chunk_id'],
                'document_id': chunk['document_id'],
                'page': chunk['page'],
                'chunk_index': chunk['chunk_index'],
                'char_count': chunk['char_count'],
                'strategy': chunk['strategy']
            }
        )
        for chunk in chunks
    ]

    print(f'Loaded {len(docs)} chunks.')

    create_vector_db(docs)
    print('Done.')