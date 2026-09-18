import api from "./api";
import type { Document } from "../types/document";

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