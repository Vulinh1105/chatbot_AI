export type IndexingStatus =
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export type DocumentType =
  | "PDF"
  | "DOCX"
  | "TXT";

export interface Document {
  id: number;
  owner_id: number;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: number;
  document_id: number;
  version_number: number;
  updated_at: string;
  is_current: boolean;
  available: boolean;
}