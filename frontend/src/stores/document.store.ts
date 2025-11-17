import { create } from 'zustand';
import { documentService } from '../services/document.service';
import { type Document } from '../types';

interface DocumentState {
  documents: Document[];
  currentDocument: Document | null;
  isLoading: boolean;
  error: string | null;
  uploadProgress: number;

  // Actions
  fetchDocuments: (params?: { skip?: number; limit?: number; status?: string }) => Promise<void>;
  fetchDocument: (documentId: string) => Promise<void>;
  uploadDocument: (file: File, templateId?: string) => Promise<Document>;
  deleteDocument: (documentId: string) => Promise<void>;
  reprocessDocument: (documentId: string, templateId: string) => Promise<void>;
  setCurrentDocument: (document: Document | null) => void;
  clearError: () => void;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  currentDocument: null,
  isLoading: false,
  error: null,
  uploadProgress: 0,

  fetchDocuments: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await documentService.getDocuments(params);
      set({ documents: response.items, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch documents',
        isLoading: false
      });
    }
  },

  fetchDocument: async (documentId) => {
    set({ isLoading: true, error: null });
    try {
      const document = await documentService.getDocument(documentId);
      set({ currentDocument: document, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch document',
        isLoading: false
      });
    }
  },

  uploadDocument: async (file, templateId) => {
    set({ isLoading: true, error: null, uploadProgress: 0 });
    try {
      const response = await documentService.uploadDocument(file, templateId);

      // Add the new document to the list
      const { documents } = get();
      set({
        documents: [response.document, ...documents],
        uploadProgress: 100,
        isLoading: false
      });

      return response.document;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to upload document',
        isLoading: false,
        uploadProgress: 0
      });
      throw error;
    }
  },

  deleteDocument: async (documentId) => {
    set({ isLoading: true, error: null });
    try {
      await documentService.deleteDocument(documentId);

      // Remove from list
      const { documents } = get();
      set({
        documents: documents.filter(doc => doc.id !== documentId),
        isLoading: false
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to delete document',
        isLoading: false
      });
      throw error;
    }
  },

  reprocessDocument: async (documentId, templateId) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await documentService.reprocessDocument(documentId, templateId);

      // Update in list
      const { documents } = get();
      set({
        documents: documents.map(doc => doc.id === documentId ? updated : doc),
        currentDocument: updated,
        isLoading: false
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to reprocess document',
        isLoading: false
      });
      throw error;
    }
  },

  setCurrentDocument: (document) => {
    set({ currentDocument: document });
  },

  clearError: () => {
    set({ error: null });
  },
}));
