/*
 * Quản lý kiểu dữ liệu cho Hội thoại, Tin nhắn và Trích dẫn Nguồn (Citation)
 */

// 1. KIỂU DỮ LIỆU TRÍCH DẪN NGUỒN (Source, Snippet, Page & Điều hướng)
export interface Citation {
  citation_id: number;       
  document_id: string;       
  document_title: string;   
  page_number?: number;     
  snippet: string;           // Đoạn trích dẫn làm bằng chứng 
  chunk_index?: number;      // Vị trí đoạn vector
  score?: number;            // Độ tin cậy / khớp ngữ nghĩa
  file_url?: string;         // Link xem file gốc
  file_type?: 'pdf' | 'docx' | 'txt' | 'web' | string; //   Loại file để hiển thị
  section_title?: string;    // Tiêu đề điều khoản 
}

// 2. KIỂU DỮ LIỆU TIN NHẮN
export interface Message {
  id: string;
  sender?: 'user' | 'assistant';                    
  role?: 'user' | 'assistant' | 'system';           // [MỚI] Chuẩn tương thích AI backend
  content: string;                                  // Nội dung câu trả lời 
  citations?: Citation[];                            // Danh sách nguồn 
  created_at?: string;                              // Thời gian gửi
  status?: 'sending' | 'streaming' | 'done' | 'error'; // Trạng thái (đang gõ/đang tải/lỗi)
  feedback?: 'thumbs_up' | 'thumbs_down' | null;     // feedback 
}

// 3. KIỂU DỮ LIỆU CUỘC HỘI THOẠI
export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

// 4. KIỂU DỮ LIỆU REQUEST GỬI TIN NHẮN ĐẾN BACKEND
export interface SendMessageRequest {
  conversation_id?: string;
  content: string;
}

// 5. KIỂU DỮ LIỆU STATE ĐIỀU HƯỚNG TRÍCH DẪN (Dùng cho UI Inspector/Drawer)
export interface ActiveCitationState {
  citation: Citation | null;
  isOpenDrawer: boolean;
}
