import { create } from 'zustand';
import { summaryService } from '../services/summary.service';
import { type Summary } from '../types';

interface SummaryState {
  summaries: Map<string, Summary>; // documentId -> Summary
  currentSummary: Summary | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchSummary: (documentId: string) => Promise<void>;
  fetchSummaryById: (summaryId: string) => Promise<void>;
  exportSummary: (summaryId: string, format: 'pdf' | 'docx') => Promise<void>;
  clearError: () => void;
}

export const useSummaryStore = create<SummaryState>((set, get) => ({
  summaries: new Map(),
  currentSummary: null,
  isLoading: false,
  error: null,

  fetchSummary: async (documentId) => {
    set({ isLoading: true, error: null });
    try {
      const summary = await summaryService.getSummary(documentId);
      const { summaries } = get();
      const newSummaries = new Map(summaries);
      newSummaries.set(documentId, summary);
      set({
        summaries: newSummaries,
        currentSummary: summary,
        isLoading: false
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error
        ? (error as any).response?.data?.detail || 'Failed to fetch summary'
        : 'Failed to fetch summary';
      set({
        error: errorMessage,
        isLoading: false
      });
    }
  },

  fetchSummaryById: async (summaryId) => {
    set({ isLoading: true, error: null });
    try {
      const summary = await summaryService.getSummaryById(summaryId);
      set({ currentSummary: summary, isLoading: false });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error
        ? (error as any).response?.data?.detail || 'Failed to fetch summary'
        : 'Failed to fetch summary';
      set({
        error: errorMessage,
        isLoading: false
      });
    }
  },

  exportSummary: async (summaryId, format) => {
    set({ isLoading: true, error: null });
    try {
      await summaryService.exportSummary(summaryId, format);
      set({ isLoading: false });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error
        ? (error as any).response?.data?.detail || 'Failed to export summary'
        : 'Failed to export summary';
      set({
        error: errorMessage,
        isLoading: false
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
