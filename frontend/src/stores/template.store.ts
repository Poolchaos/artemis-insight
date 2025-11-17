import { create } from 'zustand';
import { templateService } from '../services/template.service';
import { type Template, type CreateTemplateRequest, type UpdateTemplateRequest } from '../types';

interface TemplateState {
  templates: Template[];
  currentTemplate: Template | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchTemplates: (params?: { skip?: number; limit?: number }) => Promise<void>;
  fetchTemplate: (templateId: string) => Promise<void>;
  createTemplate: (data: CreateTemplateRequest) => Promise<Template>;
  updateTemplate: (templateId: string, data: UpdateTemplateRequest) => Promise<Template>;
  deleteTemplate: (templateId: string) => Promise<void>;
  setCurrentTemplate: (template: Template | null) => void;
  clearError: () => void;
}

export const useTemplateStore = create<TemplateState>((set, get) => ({
  templates: [],
  currentTemplate: null,
  isLoading: false,
  error: null,

  fetchTemplates: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await templateService.getTemplates(params);
      set({ templates: response.items, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch templates',
        isLoading: false
      });
    }
  },

  fetchTemplate: async (templateId) => {
    set({ isLoading: true, error: null });
    try {
      const template = await templateService.getTemplate(templateId);
      set({ currentTemplate: template, isLoading: false });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch template',
        isLoading: false
      });
    }
  },

  createTemplate: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const template = await templateService.createTemplate(data);

      // Add to list
      const { templates } = get();
      set({
        templates: [template, ...templates],
        isLoading: false
      });

      return template;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to create template',
        isLoading: false
      });
      throw error;
    }
  },

  updateTemplate: async (templateId, data) => {
    set({ isLoading: true, error: null });
    try {
      const template = await templateService.updateTemplate(templateId, data);

      // Update in list
      const { templates } = get();
      set({
        templates: templates.map(t => t.id === templateId ? template : t),
        currentTemplate: template,
        isLoading: false
      });

      return template;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to update template',
        isLoading: false
      });
      throw error;
    }
  },

  deleteTemplate: async (templateId) => {
    set({ isLoading: true, error: null });
    try {
      await templateService.deleteTemplate(templateId);

      // Remove from list
      const { templates } = get();
      set({
        templates: templates.filter(t => t.id !== templateId),
        isLoading: false
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to delete template',
        isLoading: false
      });
      throw error;
    }
  },

  setCurrentTemplate: (template) => {
    set({ currentTemplate: template });
  },

  clearError: () => {
    set({ error: null });
  },
}));
