import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import Spinner from '../ui/Spinner';
import Card, { CardContent, CardHeader } from '../ui/Card';
import { useDocumentStore } from '../../stores/document.store';
import { useSummaryStore } from '../../stores/summary.store';
import { documentService } from '../../services/document.service';

export function DocumentViewer() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState(0);

  const { currentDocument, isLoading: docLoading, error: docError, fetchDocument } = useDocumentStore();
  const { currentSummary, isLoading: summaryLoading, error: summaryError, fetchSummary, exportSummary } = useSummaryStore();

  useEffect(() => {
    if (id) {
      fetchDocument(id);
      fetchSummary(id);
    }
  }, [id, fetchDocument, fetchSummary]);

  const handleBack = () => {
    navigate('/documents');
  };

  const handleDownloadPDF = () => {
    if (!id) return;
    const downloadUrl = documentService.getDocumentDownloadUrl(id);
    window.open(downloadUrl, '_blank');
  };

  const handleExportSummary = async () => {
    if (!currentSummary) return;

    try {
      const content = await exportSummary(currentSummary.id);

      // Create a blob and download
      const blob = new Blob([content], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `summary-${currentDocument?.filename || 'document'}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      // Error handled by store
    }
  };

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

  // Parse summary content into sections
  const sections = currentSummary?.content
    ? currentSummary.content.split('\n\n').filter(s => s.trim())
    : [];

  if (docLoading || summaryLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (docError || summaryError) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back
        </Button>
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">
            {docError || summaryError}
          </p>
        </div>
      </div>
    );
  }

  if (!currentDocument) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">Document not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {currentDocument.filename}
              </h1>
              <Badge variant={getStatusBadgeVariant(currentDocument.status)}>
                {currentDocument.status || 'pending'}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {currentDocument.page_count} pages • Uploaded {new Date(currentDocument.uploaded_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleDownloadPDF}>
            <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
            Download PDF
          </Button>
          {currentSummary && (
            <Button variant="outline" onClick={handleExportSummary}>
              <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
              Export Summary
            </Button>
          )}
        </div>
      </div>

      {/* Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PDF Viewer */}
        <Card className="lg:sticky lg:top-6 h-fit">
          <CardHeader>
            <div className="flex items-center gap-2">
              <DocumentTextIcon className="h-5 w-5 text-gray-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Document
              </h2>
            </div>
          </CardHeader>
          <CardContent>
            <div className="aspect-[8.5/11] bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
              <div className="text-center">
                <DocumentTextIcon className="mx-auto h-16 w-16 text-gray-400 dark:text-gray-500 mb-4" />
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  PDF Viewer
                </p>
                <Button onClick={handleDownloadPDF}>
                  View Full PDF
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Summary */}
        <div className="space-y-6">
          {currentSummary ? (
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Summary
                </h2>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Section Tabs */}
                {sections.length > 1 && (
                  <div className="flex flex-wrap gap-2">
                    {sections.map((_, index) => (
                      <button
                        key={index}
                        onClick={() => setActiveSection(index)}
                        className={`
                          px-4 py-2 rounded-md text-sm font-medium transition-colors
                          ${activeSection === index
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                          }
                        `}
                      >
                        Section {index + 1}
                      </button>
                    ))}
                  </div>
                )}

                {/* Summary Content */}
                <div className="prose dark:prose-invert max-w-none">
                  <div className="whitespace-pre-wrap text-gray-700 dark:text-gray-300">
                    {sections[activeSection] || currentSummary.content}
                  </div>
                </div>

                {/* Template Info */}
                {currentSummary.template_id && (
                  <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Generated using custom template
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Spinner className="mx-auto mb-4" />
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {currentDocument.status === 'processing'
                    ? 'Summary is being generated...'
                    : currentDocument.status === 'pending'
                    ? 'Document is queued for processing...'
                    : currentDocument.status === 'failed'
                    ? 'Failed to generate summary'
                    : 'No summary available'
                  }
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
