import api from '../lib/api';
import { type Summary, type SummaryListItem } from '../types';

export const summaryService = {
  /**
   * List all summaries for the current user
   */
  async listSummaries(params?: {
    document_id?: string;
    template_id?: string;
    status?: 'processing' | 'completed' | 'failed';
    skip?: number;
    limit?: number;
  }): Promise<SummaryListItem[]> {
    const queryParams = new URLSearchParams();
    if (params?.document_id) queryParams.append('document_id', params.document_id);
    if (params?.template_id) queryParams.append('template_id', params.template_id);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const url = `/api/summaries${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    const response = await api.get<SummaryListItem[]>(url);
    return response.data;
  },

  /**
   * Create a new summary job
   */
  async createSummary(documentId: string, templateId: string): Promise<{ job_id: string; status: string; message: string }> {
    const response = await api.post<{ job_id: string; celery_task_id: string; status: string; message: string }>(
      `/api/summaries?document_id=${documentId}&template_id=${templateId}`
    );
    return response.data;
  },

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
   * Export summary as PDF or DOCX
   */
  async exportSummary(summaryId: string, format: 'pdf' | 'docx'): Promise<void> {
    const response = await api.get(`/api/summaries/${summaryId}/export/${format}`, {
      responseType: 'blob',
    });

    // Create download link
    const blob = new Blob([response.data], {
      type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;

    // Extract filename from content-disposition header if available
    const contentDisposition = response.headers['content-disposition'];
    let filename = `summary-${summaryId}.${format}`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Delete a summary
   */
  async deleteSummary(summaryId: string): Promise<void> {
    await api.delete(`/api/summaries/${summaryId}`);
  },

  /**
   * Retry a failed summary generation
   */
  async retrySummary(summaryId: string): Promise<{ job_id: string; status: string; message: string }> {
    const response = await api.post<{ job_id: string; celery_task_id: string; status: string; message: string }>(
      `/api/summaries/${summaryId}/retry`
    );
    return response.data;
  },
};
