import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from prompt import qa_prompt

# Import trực tiếp hàm retrieve từ T13 (retrieval.py)
try:
    from retrieval import retrieve
except ImportError:
    retrieve = None

load_dotenv()

def generate_answer(query: str, context_chunks: list) -> str:
    """
    Hàm sinh câu trả lời bằng OpenAI dựa trên context.
    Nhận đầu vào là danh sách đối tượng Document (từ retrieval.py) hoặc chuỗi str.
    """
    # Nếu T13 không tìm thấy chunk nào phù hợp (không vượt qua score_threshold = 0.2)
    if not context_chunks:
        return "Tài liệu hiện tại không đề cập vấn đề này."

    # Lấy thuộc tính page_content từ các Document object của FAISS
    formatted_chunks = [
        doc.page_content if hasattr(doc, "page_content") else str(doc)
        for doc in context_chunks
    ]
    
    context_text = "\n\n---\n\n".join(formatted_chunks)
    
    llm = ChatOpenAI(model="gpt-5.4-nano", temperature=0)
    
    chain = qa_prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "context": context_text,
        "query": query
    })
    
    return response


if __name__ == "__main__":
    print("Khởi chạy chatbot_AI\n")
    
    while True:
        query = input('Question (type "exit" to quit): ')
        
        if query.strip().lower() == 'exit':
            print('program exited.')
            break
            
        if not query.strip():
            continue

        if retrieve:
            results = retrieve(query)
            print(f'\n[T13] Tìm thấy {len(results)} chunks phù hợp từ FAISS.\n')
            answer = generate_answer(query, results)
            
            print(f"AI Answer:\n{answer}\n")
            print("=" * 60 + "\n")
        else:
            print("\n[Lỗi] Không thể tìm thấy file retrieval.py cùng thư mục để import hàm retrieve().\n")