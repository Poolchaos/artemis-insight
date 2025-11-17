import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RectangleStackIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import Spinner from '../ui/Spinner';
import Card, { CardContent } from '../ui/Card';
import Modal from '../ui/Modal';
import { useTemplateStore } from '../../stores/template.store';

export function TemplateList() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<string | null>(null);

  const { templates, isLoading, error, fetchTemplates, deleteTemplate } = useTemplateStore();

  useEffect(() => {
    fetchTemplates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredTemplates = (templates || []).filter((template) =>
    template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    template.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreate = () => {
    navigate('/templates/create');
  };

  const handleEdit = (templateId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/templates/${templateId}/edit`);
  };

  const handleDeleteClick = (templateId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setTemplateToDelete(templateId);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!templateToDelete) return;

    try {
      await deleteTemplate(templateToDelete);
      setDeleteModalOpen(false);
      setTemplateToDelete(null);
    } catch {
      // Error handled by store
    }
  };

  const handleView = (templateId: string) => {
    navigate(`/templates/${templateId}`);
  };

  if (isLoading && (!templates || templates.length === 0)) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        {/* Search */}
        <div className="flex-1 w-full relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="
              w-full pl-10 pr-4 py-2
              border border-gray-300 dark:border-gray-600 rounded-md
              bg-white dark:bg-gray-800
              text-gray-900 dark:text-gray-100
              placeholder-gray-400 dark:placeholder-gray-500
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
            "
          />
        </div>

        {/* Create Button */}
        <Button onClick={handleCreate}>
          <PlusIcon className="h-5 w-5 mr-2" />
          Create Template
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Templates Grid */}
      {filteredTemplates.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <RectangleStackIcon className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
              {searchQuery ? 'No templates found' : 'No templates yet'}
            </h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {searchQuery
                ? 'Try adjusting your search'
                : 'Create your first template to get started'
              }
            </p>
            {!searchQuery && (
              <div className="mt-6">
                <Button onClick={handleCreate}>
                  <PlusIcon className="h-5 w-5 mr-2" />
                  Create Template
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.map((template) => (
            <Card
              key={template.id}
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleView(template.id)}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <RectangleStackIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    {template.is_system && (
                      <Badge variant="info">System</Badge>
                    )}
                  </div>

                  {!template.is_system && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => handleEdit(template.id, e)}
                        className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                        title="Edit"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteClick(template.id, e)}
                        className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                        title="Delete"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  )}
                </div>

                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  {template.name}
                </h3>

                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-4">
                  {template.description}
                </p>

                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>{template.sections?.length || template.fields?.length || 0} sections</span>
                  {!template.is_system && (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && templates.length > 0 && (
        <div className="flex items-center justify-center py-4">
          <Spinner />
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Delete Template"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Are you sure you want to delete this template? This action cannot be undone.
          </p>

          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setDeleteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteConfirm}
              isLoading={isLoading}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
