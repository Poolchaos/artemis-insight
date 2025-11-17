import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Card, { CardContent, CardHeader } from '../ui/Card';
import { useTemplateStore } from '../../stores/template.store';
import { type TemplateSection } from '../../types';

interface TemplateFormProps {
  templateId?: string;
  mode: 'create' | 'edit';
}

export function TemplateForm({ templateId, mode }: TemplateFormProps) {
  const navigate = useNavigate();
  const { currentTemplate, isLoading, error, fetchTemplate, createTemplate, updateTemplate } = useTemplateStore();

  // Initialize default sections
  const defaultSections: TemplateSection[] = useMemo(() => [{ name: '', prompt: '' }], []);

  // Derive initial values from currentTemplate
  const initialName = mode === 'edit' && currentTemplate ? currentTemplate.name : '';
  const initialDescription = mode === 'edit' && currentTemplate ? currentTemplate.description : '';
  const initialSections = useMemo(() => {
    if (mode === 'edit' && currentTemplate?.fields && currentTemplate.fields.length > 0) {
      return currentTemplate.fields.map(field => ({
        name: field,
        prompt: currentTemplate.prompt_template || ''
      }));
    }
    return defaultSections;
  }, [mode, currentTemplate, defaultSections]);

  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [sections, setSections] = useState<TemplateSection[]>(initialSections);

  useEffect(() => {
    if (mode === 'edit' && templateId) {
      fetchTemplate(templateId);
    }
  }, [mode, templateId, fetchTemplate]);

  // Update form when template loads
  // This is intentional for form initialization from fetched data
  useEffect(() => {
    if (mode === 'edit' && currentTemplate) {
      setName(currentTemplate.name);
      setDescription(currentTemplate.description);

      // Handle both new sections format and legacy fields format
      if (currentTemplate.sections && currentTemplate.sections.length > 0) {
        setSections(
          currentTemplate.sections.map(section => ({
            name: section.name || section.title || '',
            prompt: section.prompt || section.guidance_prompt || ''
          }))
        );
      } else if (currentTemplate.fields && currentTemplate.fields.length > 0) {
        setSections(
          currentTemplate.fields.map(field => ({
            name: field,
            prompt: currentTemplate.prompt_template || ''
          }))
        );
      }
    }
  }, [currentTemplate?.id, mode, currentTemplate]); // Intentional: Initialize form from loaded data

  const handleAddSection = () => {
    setSections([...sections, { name: '', prompt: '' }]);
  };

  const handleRemoveSection = (index: number) => {
    setSections(sections.filter((_, i) => i !== index));
  };

  const handleSectionChange = (index: number, field: keyof TemplateSection, value: string) => {
    const updated = [...sections];
    updated[index] = { ...updated[index], [field]: value };
    setSections(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!name.trim()) {
      alert('Please enter a template name');
      return;
    }

    if (!description.trim()) {
      alert('Please enter a template description');
      return;
    }

    if (sections.length === 0) {
      alert('Please add at least one section');
      return;
    }

    for (const section of sections) {
      if (!(section.name || section.title)?.trim() || !(section.prompt || section.guidance_prompt)?.trim()) {
        alert('Please fill in all section fields');
        return;
      }
    }

    try {
      if (mode === 'create') {
        await createTemplate({
          name: name.trim(),
          description: description.trim(),
          target_length: '5-10 pages', // Default value
          sections: sections.map((s, idx) => ({
            title: (s.name || s.title || '').trim(),
            guidance_prompt: (s.prompt || s.guidance_prompt || '').trim(),
            order: idx + 1,
            required: true
          }))
        });
      } else if (mode === 'edit' && templateId) {
        await updateTemplate(templateId, {
          name: name.trim(),
          description: description.trim(),
          target_length: '5-10 pages', // Default value
          sections: sections.map((s, idx) => ({
            title: (s.name || s.title || '').trim(),
            guidance_prompt: (s.prompt || s.guidance_prompt || '').trim(),
            order: idx + 1,
            required: true
          }))
        });
      }

      navigate('/templates');
    } catch {
      // Error handled by store
    }
  };

  const handleCancel = () => {
    navigate('/templates');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Information */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Basic Information
          </h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="Template Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Legal Document Summary"
            required
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this template is used for..."
              rows={3}
              className="
                w-full px-3 py-2
                border border-gray-300 dark:border-gray-600 rounded-md
                bg-white dark:bg-gray-800
                text-gray-900 dark:text-gray-100
                placeholder-gray-400 dark:placeholder-gray-500
                focus:ring-2 focus:ring-blue-500 focus:border-transparent
                resize-none
              "
              required
            />
          </div>
        </CardContent>
      </Card>

      {/* Sections */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Template Sections
            </h2>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddSection}
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add Section
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {sections.map((section, index) => (
            <div
              key={index}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg space-y-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Section {index + 1}
                </h3>
                {sections.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveSection(index)}
                    className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                )}
              </div>

              <Input
                label="Section Name"
                value={section.name}
                onChange={(e) => handleSectionChange(index, 'name', e.target.value)}
                placeholder="e.g., Key Points, Summary, Analysis"
                required
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Section Prompt
                </label>
                <textarea
                  value={section.prompt}
                  onChange={(e) => handleSectionChange(index, 'prompt', e.target.value)}
                  placeholder="Enter the prompt that will guide the AI in generating this section..."
                  rows={4}
                  className="
                    w-full px-3 py-2
                    border border-gray-300 dark:border-gray-600 rounded-md
                    bg-white dark:bg-gray-800
                    text-gray-900 dark:text-gray-100
                    placeholder-gray-400 dark:placeholder-gray-500
                    focus:ring-2 focus:ring-blue-500 focus:border-transparent
                    resize-none
                  "
                  required
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  This prompt will be used to generate content for this section
                </p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={handleCancel}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          isLoading={isLoading}
        >
          {mode === 'create' ? 'Create Template' : 'Update Template'}
        </Button>
      </div>
    </form>
  );
}
