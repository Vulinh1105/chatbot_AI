
 * Quản lý kiểu dữ liệu cho Hội thoại, Tin nhắn và Trích dẫn Nguồn (Citation)
// 1. KIỂU DỮ LIỆU TRÍCH DẪN NGUỒN (Phục vụ: Source, Snippet, Page & Điều hướng)
export interface Citation 
{
  citation_id: number;      
  document_id: string;      
  document_title: string;     
  page_number: number;       
  snippet: string;           // Đoạn văn bản nguyên tác được trích làm bằng chứng (SNIPPET)
  chunk_index?: number;      // Thứ tự đoạn (chunk) trong database vector
  score?: number;            // Độ tương đồng/khớp ngữ nghĩa 
  file_url?: string;         // Đường dẫn URL 
}

// 2. KIỂU DỮ LIỆU TIN NHẮN 
export interface Message 
{
  id: string;
  sender: 'user' | 'assistant'; 
  content: string;              
  citations?: Citation[];        // Danh sách các nguồn/snippet/page đi kèm câu trả lời
  created_at: string;        
}

// 3. KIỂU DỮ LIỆU CUỘC HỘI THOẠI 
export interface Conversation 
{
  id: string;
  title: string;                
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

// 4. KIỂU DỮ LIỆU REQUEST GỬI TIN NHẮN ĐẾN BACKEND
export interface SendMessageRequest 
{
  conversation_id?: string;
  content: string;
}

// 5. KIỂU DỮ LIỆU STATE ĐIỀU HƯỚNG TRÍCH DẪN (Dùng cho UI Inspector/Drawer)
export interface ActiveCitationState 
{
  citation: Citation | null;
  isOpenDrawer: boolean;
}
=======

