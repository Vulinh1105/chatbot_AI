import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
load_dotenv()
SYSTEM_PROMPT_TEMPLATE = """Bạn là trợ lý AI tra cứu tài liệu nội bộ của công ty. Nhiệm vụ của bạn là trả lời câu hỏi của nhân viên dựa CHỈ vào ngữ cảnh tài liệu được cung cấp trong thẻ <context> bên dưới.

<context>
{context}
</context>

Quy tắc nghiêm ngặt:
1. Chỉ sử dụng thông tin nằm trong thẻ <context> để trả lời.
2. Tuyệt đối không sử dụng kiến thức bên ngoài hoặc tự suy đoán.
3. Trước khi trả lời, phải kiểm tra xem <context> có thực sự chứa thông tin để trả lời đúng ý câu hỏi hay không.
4. Không được trả lời một câu hỏi khác chỉ vì <context> có chứa một vài từ khóa giống với câu hỏi.
5. Nếu câu hỏi không được tài liệu đề cập hoặc ngữ cảnh không đủ để trả lời đúng câu hỏi, hãy trả lời:
"Tài liệu hiện tại không đề cập vấn đề này."
6. Nếu chỉ một phần câu hỏi được tài liệu hỗ trợ, chỉ trả lời phần được hỗ trợ và nói rõ phần còn lại không được đề cập.
7. Không được tự suy đoán, bổ sung hoặc diễn giải thông tin không có trong tài liệu.
8. Nếu câu hỏi mơ hồ hoặc không có ý nghĩa rõ ràng trong ngữ cảnh tài liệu, không được tự suy diễn ý định của người dùng. Hãy trả lời:
"Tài liệu hiện tại không đề cập vấn đề này."
"""

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_TEMPLATE),
    ("human", "{query}")
])

# llm
# Import trực tiếp hàm retrieve từ T13 (retrieval.py)
# try:
#     from retrieval import retrieve
# except ImportError:
#     retrieve = None
# --> viết vào pipeline


def generate_answer(query: str, context_chunks) -> str:
    """
    Sinh câu trả lời bằng LLM.

    Input:
        query:
            Câu hỏi người dùng.

        context_chunks:
            List[Document] từ Retrieval/Reranking.

    Output:
        str
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



    # test
    # # Debug context trước khi gửi LLM
    # print("\n===== CONTEXT SENT TO LLM =====")
    # print(context_text)
    # print("================================\n")
    #



    llm = ChatOpenAI(model="gpt-5.4-nano", temperature=0)
    
    chain = (
        qa_prompt
        | llm
        | StrOutputParser()
    )





    # messages = qa_prompt.format_messages(
    #     context=context_text,
    #     query=query
    # )


    # test
    # print("\n===== ACTUAL PROMPT =====")
    # for message in messages:
    #     print(f"\n[{message.type}]")
    #     print(message.content)
    # print("=========================\n")



    response = chain.invoke({
        "context": context_text,
        "query": query
    })


    # test
    # print("\n===== RAW LLM RESPONSE =====")
    # print(repr(response))
    # print("============================\n")



    return response.strip()

#
# if __name__ == "__main__":
#     print("Khởi chạy chatbot_AI\n")
#
#     while True:
#         query = input('Question (type "exit" to quit): ')
#
#         if query.strip().lower() == 'exit':
#             print('program exited.')
#             break
#
#         if not query.strip():
#             continue
#
#         if retrieve:
#             results = retrieve(query)
#             print(f'\n[T13] Tìm thấy {len(results)} chunks phù hợp từ FAISS.\n')
#             answer = generate_answer(query, results)
#
#             print(f"AI Answer:\n{answer}\n")
#             print("=" * 60 + "\n")
#         else:
#             print("\n[Lỗi] Không thể tìm thấy file retrieval.py cùng thư mục để import hàm retrieve().\n")