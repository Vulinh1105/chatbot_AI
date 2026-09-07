from faiss.swigfaiss import DistanceComputer
from jinja2 import meta
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from pathlib import Path
import os
import json
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

# DATA_PATH='../data'
DATA_PATH = Path(__file__).resolve().parent.parent.parent / 'data'
FAISS_PATH = Path(__file__).resolve().parent.parent.parent / 'faiss_index'

def create_vector_db(docs):

    # embedding
    embeddings = OpenAIEmbeddings(
        model='text-embedding-3-large'
    )

    print('Creating embeddings...')
    db = FAISS.from_documents(docs, embeddings, distance_strategy=DistanceStrategy.COSINE)
    db.save_local(FAISS_PATH)
    print('Faiss index created successfully.')

    return db

if __name__ == '__main__':
    # # read json
    # json_path = DATA_PATH / 'chunks.json'
    # with open(json_path, 'r', encoding='utf-8') as f:
    #     chunks = json.load(f)
    #
    # # json -> doc
    # docs = [
    #     Document(
    #         page_content=chunk['page_content'],
    #         metadata=chunk.get('metadata', {})
    #     )
    #     for chunk in chunks
    # ]

    print(f'Loaded {len(docs)} chunks.')

    create_vector_db(docs)