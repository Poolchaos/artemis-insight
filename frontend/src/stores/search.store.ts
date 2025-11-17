import { create } from 'zustand';
import { searchService, type SearchRequest, type SearchResponse } from '../services/search.service';

interface SearchState {
  currentSearch: SearchResponse | null;
  searchHistory: SearchResponse[];
  isLoading: boolean;
  error: string | null;

  // Actions
  searchDocument: (params: SearchRequest) => Promise<void>;
  clearSearch: () => void;
  clearError: () => void;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  currentSearch: null,
  searchHistory: [],
  isLoading: false,
  error: null,

  searchDocument: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await searchService.searchDocument(params);

      const { searchHistory } = get();
      set({
        currentSearch: response,
        searchHistory: [response, ...searchHistory.slice(0, 9)], // Keep last 10
        isLoading: false
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to search document'
        : 'Failed to search document';
      set({
        error: errorMessage,
        isLoading: false
      });
    }
  },

  clearSearch: () => {
    set({ currentSearch: null, error: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));
