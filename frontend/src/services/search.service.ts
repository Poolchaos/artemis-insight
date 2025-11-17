import api from '../lib/api';
import { type SnippetResult } from '../types';

export interface SearchRequest {
  document_id: string;
  query: string;
  min_similarity?: number;
  top_k?: number;
}

export interface SearchResponse {
  query: string;
  results: SnippetResult[];
  total_results: number;
}

export const searchService = {
  /**
   * Perform semantic search on a document
   */
  async searchDocument(params: SearchRequest): Promise<SearchResponse> {
    const { document_id, ...searchParams } = params;
    const response = await api.post<SearchResponse>(`/api/documents/${document_id}/search`, searchParams);
    return response.data;
  },
};
