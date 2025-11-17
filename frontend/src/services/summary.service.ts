import api from '../lib/api';
import { type Summary } from '../types';

export const summaryService = {
  /**
   * Get summary for a document
   */
  async getSummary(documentId: string): Promise<Summary> {
    const response = await api.get<Summary>(`/api/summaries/document/${documentId}`);
    return response.data;
  },

  /**
   * Get summary by ID
   */
  async getSummaryById(summaryId: string): Promise<Summary> {
    const response = await api.get<Summary>(`/api/summaries/${summaryId}`);
    return response.data;
  },

  /**
   * Export summary as text
   */
  async exportSummary(summaryId: string): Promise<string> {
    const response = await api.get<{ content: string }>(`/api/summaries/${summaryId}/export`);
    return response.data.content;
  },
};
