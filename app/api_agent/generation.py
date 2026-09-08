import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from prompt import qa_prompt

load_dotenv()

def generate_answer(query: str, context_chunks: list[str]) -> str:
    """
    Hàm sinh câu trả lời bằng OpenAI dựa trên context.
    """
    context_text = "\n\n---\n\n".join(context_chunks)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    

    chain = qa_prompt | llm | StrOutputParser()
    response = chain.invoke({
        "context": context_text,
        "query": query
    })
    
    return response

# KHU VỰC CHẠY TEST ĐỘC LẬP (MOCK DATA)
if __name__ == "__main__":
#    os.environ["OPENAI_API_KEY"] = "sk-..." 
    
    print(" Đang khởi động test cho module  (Generation)...\n")

    mock_chunks = [ 
        "Chính sách nghỉ phép: Nhân viên chính thức được nghỉ 12 ngày phép năm.",
        "Nhân viên thử việc (2 tháng đầu) không được tính để hưởng phép năm."
    ]
    
    # 2. Test Case 1: Câu hỏi CÓ trong tài liệu
    query_1 = "Nhân viên thử việc có được tính phép năm không?"
    print(f"User hỏi: {query_1}")
    print(f"AI đáp:   {generate_answer(query_1, mock_chunks)}\n")
    
    # 3. Test Case 2: Câu hỏi KHÔNG CÓ trong tài liệu (Test Guardrail MVP)
    query_2 = "Công ty có hỗ trợ chi phí gửi xe không?"
    print(f"User hỏi: {query_2}")
    print(f"AI đáp:   {generate_answer(query_2, mock_chunks)}\n")