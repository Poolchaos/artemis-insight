import api from '../lib/api';
import { type Document, type DocumentListResponse, type DocumentUploadResponse } from '../types';

export const documentService = {
  /**
   * Upload a document with optional template
   */
  async uploadDocument(file: File, templateId?: string): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (templateId) {
      formData.append('template_id', templateId);
    }

    const response = await api.post<DocumentUploadResponse>('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Get all documents for the current user
   */
  async getDocuments(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<DocumentListResponse> {
    const response = await api.get<DocumentListResponse>('/api/documents', { params });
    return response.data;
  },

  /**
   * Get a specific document by ID
   */
  async getDocument(documentId: string): Promise<Document> {
    const response = await api.get<Document>(`/api/documents/${documentId}`);
    return response.data;
  },

  /**
   * Delete a document
   */
  async deleteDocument(documentId: string): Promise<void> {
    await api.delete(`/api/documents/${documentId}`);
  },

  /**
   * Reprocess a document with a different template
   */
  async reprocessDocument(documentId: string, templateId: string): Promise<Document> {
    const response = await api.post<Document>(`/api/documents/${documentId}/reprocess`, {
      template_id: templateId,
    });
    return response.data;
  },

  /**
   * Download document file
   */
  getDocumentDownloadUrl(documentId: string): string {
    return `${api.defaults.baseURL}/api/documents/${documentId}/download`;
  },
};
