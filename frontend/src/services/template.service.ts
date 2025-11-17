import api from '../lib/api';
import { type Template, type TemplateListResponse, type CreateTemplateRequest, type UpdateTemplateRequest } from '../types';

export const templateService = {
  /**
   * Get all templates for the current user
   */
  async getTemplates(params?: {
    skip?: number;
    limit?: number;
  }): Promise<TemplateListResponse> {
    const response = await api.get<TemplateListResponse>('/templates', { params });
    return response.data;
  },

  /**
   * Get a specific template by ID
   */
  async getTemplate(templateId: string): Promise<Template> {
    const response = await api.get<Template>(`/templates/${templateId}`);
    return response.data;
  },

  /**
   * Create a new template
   */
  async createTemplate(data: CreateTemplateRequest): Promise<Template> {
    const response = await api.post<Template>('/templates', data);
    return response.data;
  },

  /**
   * Update an existing template
   */
  async updateTemplate(templateId: string, data: UpdateTemplateRequest): Promise<Template> {
    const response = await api.put<Template>(`/templates/${templateId}`, data);
    return response.data;
  },

  /**
   * Delete a template
   */
  async deleteTemplate(templateId: string): Promise<void> {
    await api.delete(`/templates/${templateId}`);
  },
};
