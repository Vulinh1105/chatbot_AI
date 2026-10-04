import api from "./api";
import type {
  Document,
  DocumentVersion,
} from "../types/document";

export const getDocuments = async (): Promise<Document[]> => {
  const response = await api.get(
    "/api/v1/documents/?skip=0&limit=100"
  );

  const data = response.data;

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.items)) {
    return data.items;
  }

  if (Array.isArray(data?.documents)) {
    return data.documents;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  return [];
};

export const uploadDocument = async (
  file: File
) => {
  const formData = new FormData();
  formData.append("file", file);

  return api.post("/api/v1/documents/", formData);
};

export const deleteDocument = async (
  documentId: number
) => {
  return api.delete(
    `/api/v1/documents/${documentId}`
  );
};

export const getMockDocumentVersions = async (
  documentId: number
): Promise<DocumentVersion[]> => {
  await new Promise((resolve) =>
    setTimeout(resolve, 500)
  );

  return [
    {
      id: 3,
      document_id: documentId,
      version_number: 3,
      updated_at: "2026-09-19T14:30:00",
      is_current: true,
      available: true,
    },
    {
      id: 2,
      document_id: documentId,
      version_number: 2,
      updated_at: "2026-09-15T10:20:00",
      is_current: false,
      available: true,
    },
    {
      id: 1,
      document_id: documentId,
      version_number: 1,
      updated_at: "2026-09-10T08:15:00",
      is_current: false,
      available: true,
    },
  ];
};

export const mockRollbackDocumentVersion = async (
  documentId: number,
  versionId: number
): Promise<void> => {
  console.log(
    `Mock rollback: document ${documentId} -> version ${versionId}`
  );

  // Giả lập backend rollback + re-index vector
  await new Promise((resolve) =>
    setTimeout(resolve, 1500)
  );
};