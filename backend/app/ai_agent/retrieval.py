
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from dotenv import load_dotenv


load_dotenv()


FAISS_PATH = Path(__file__).resolve().parent.parent.parent / 'faiss_index'
embedder = OpenAIEmbeddings(
    model='text-embedding-3-large'
)

# lấy phaanf embedding ở T12
db = FAISS.load_local(
    FAISS_PATH,
    embedder,
    allow_dangerous_deserialization=True
)

retriever=db.as_retriever(
    search_type='similarity_score_threshold',
    search_kwargs={'k': 3, 'score_threshold': 0.2}
)
print('done topK + score')


# Hàm Retrieval
def retrieve(query):
    results = retriever.invoke(query)
    return results


if __name__ == '__main__':
    query = input('Question: ')

    results = retrieve(query)

    print(f'\nTìm thấy {len(results)} chunks:\n')

    for i, doc in enumerate(results, start=1):
        print(f'--- Result {i} ---')
        print('Content:', doc.page_content)
        print('Metadata:', doc.metadata)
