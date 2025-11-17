import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PencilIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import Spinner from '../ui/Spinner';
import Card, { CardContent, CardHeader } from '../ui/Card';
import { useTemplateStore } from '../../stores/template.store';

export function TemplateView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentTemplate, isLoading, error, fetchTemplate } = useTemplateStore();

  useEffect(() => {
    if (id) {
      fetchTemplate(id);
    }
  }, [id, fetchTemplate]);

  const handleEdit = () => {
    navigate(`/templates/${id}/edit`);
  };

  const handleBack = () => {
    navigate('/templates');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
      </div>
    );
  }

  if (!currentTemplate) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">Template not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {currentTemplate.name}
              </h1>
              {currentTemplate.is_system && (
                <Badge variant="info">System</Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {currentTemplate.description}
            </p>
          </div>
        </div>

        {!currentTemplate.is_system && (
          <Button onClick={handleEdit}>
            <PencilIcon className="h-5 w-5 mr-2" />
            Edit Template
          </Button>
        )}
      </div>

      {/* Template Details */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Template Sections
          </h2>
        </CardHeader>
        <CardContent className="space-y-6">
          {currentTemplate.sections && currentTemplate.sections.length > 0 ? (
            currentTemplate.sections
              .sort((a, b) => (a.order || 0) - (b.order || 0))
              .map((section, index) => (
                <div
                  key={index}
                  className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {section.order || (index + 1)}. {section.title}
                    </h3>
                    {section.required && (
                      <Badge variant="info">Required</Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                    {section.guidance_prompt}
                  </p>
                </div>
              ))
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No sections defined
            </p>
          )}
        </CardContent>
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Metadata
          </h2>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="font-medium text-gray-500 dark:text-gray-400">Type</dt>
              <dd className="mt-1 text-gray-900 dark:text-gray-100">
                {currentTemplate.is_system ? 'System Template' : 'Custom Template'}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-500 dark:text-gray-400">Sections</dt>
              <dd className="mt-1 text-gray-900 dark:text-gray-100">
                {currentTemplate.sections?.length || 0}
              </dd>
            </div>
            {currentTemplate.created_at && (
              <div>
                <dt className="font-medium text-gray-500 dark:text-gray-400">Created</dt>
                <dd className="mt-1 text-gray-900 dark:text-gray-100">
                  {new Date(currentTemplate.created_at).toLocaleDateString()}
                </dd>
              </div>
            )}
            {currentTemplate.updated_at && (
              <div>
                <dt className="font-medium text-gray-500 dark:text-gray-400">Last Updated</dt>
                <dd className="mt-1 text-gray-900 dark:text-gray-100">
                  {new Date(currentTemplate.updated_at).toLocaleDateString()}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
