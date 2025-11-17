import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  TrashIcon,
  EyeIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import Spinner from '../ui/Spinner';
import Card, { CardContent } from '../ui/Card';
import Modal from '../ui/Modal';
import { useDocumentStore } from '../../stores/document.store';
import { formatRelativeTime } from '../../lib/utils';

export function DocumentList() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<{ id: string; filename: string } | null>(null);

  const { documents, isLoading, error, fetchDocuments, deleteDocument } = useDocumentStore();

  useEffect(() => {
    fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredDocuments = (documents || []).filter((doc) => {
    if (!doc || !doc.filename) return false;
    const matchesSearch = doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadgeVariant = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleDelete = async (documentId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDocumentToDelete({ id: documentId, filename });
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (documentToDelete) {
      try {
        await deleteDocument(documentToDelete.id);
        setDeleteModalOpen(false);
        setDocumentToDelete(null);
      } catch {
        // Error handled by store
        setDeleteModalOpen(false);
      }
    }
  };

  const handleView = (documentId: string) => {
    navigate(`/documents/${documentId}`);
  };

  if (isLoading && (!documents || documents.length === 0)) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents..."
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

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <FunnelIcon className="h-5 w-5 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="
                  px-3 py-2
                  border border-gray-300 dark:border-gray-600 rounded-md
                  bg-white dark:bg-gray-800
                  text-gray-900 dark:text-gray-100
                  focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {/* Refresh Button */}
            <Button
              variant="outline"
              onClick={() => fetchDocuments()}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Documents List */}
      {filteredDocuments.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
              {searchQuery || statusFilter !== 'all' ? 'No documents found' : 'No documents yet'}
            </h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Upload your first document to get started'
              }
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredDocuments.map((document) => (
            <Card
              key={document.id}
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleView(document.id)}
            >
              <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="shrink-0">
                      <DocumentTextIcon className="h-10 w-10 text-blue-600 dark:text-blue-400" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 truncate">
                          {document.filename}
                        </h3>
                        <Badge variant={getStatusBadgeVariant(document.status)}>
                          {document.status || 'pending'}
                        </Badge>
                      </div>

                      <div className="mt-2 flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                        <span>{document.page_count || 0} pages</span>
                        <span>•</span>
                        <span>
                          {document.upload_date
                            ? formatRelativeTime(new Date(document.upload_date))
                            : document.uploaded_at
                              ? formatRelativeTime(new Date(document.uploaded_at))
                              : 'Unknown date'
                          }
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        handleView(document.id);
                      }}
                    >
                      <EyeIcon className="h-4 w-4 mr-1" />
                      View
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e: React.MouseEvent) => handleDelete(document.id, document.filename, e)}
                      className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && documents.length > 0 && (
        <div className="flex items-center justify-center py-4">
          <Spinner />
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Delete Document"
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete}>
              Delete
            </Button>
          </div>
        }
      >
        <p className="text-gray-700 dark:text-gray-300">
          Are you sure you want to delete <strong>{documentToDelete?.filename}</strong>? This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
