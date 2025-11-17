import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import Spinner from '../ui/Spinner';
import { useDocumentStore } from '../../stores/document.store';
import { documentService } from '../../services/document.service';

export function DocumentViewer() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState<number>(0);

  const { currentDocument, isLoading, error, fetchDocument } = useDocumentStore();

  useEffect(() => {
    if (id) {
      fetchDocument(id);
    }
  }, [id, fetchDocument]);

  // Load PDF blob with authentication
  useEffect(() => {
    let cancelled = false;

    if (id && currentDocument) {
      console.log('Loading PDF for document:', id);
      console.log('Current document status:', currentDocument.status);

      setLoadingProgress(0);

      documentService.downloadDocumentBlob(id, (progress) => {
        if (!cancelled) {
          setLoadingProgress(progress);
          console.log('Download progress:', progress + '%');
        }
      })
        .then((blob) => {
          console.log('downloadDocumentBlob promise resolved');
          if (!cancelled) {
            console.log('PDF blob loaded, size:', blob.size, 'type:', blob.type);
            const url = URL.createObjectURL(blob);
            console.log('Created blob URL:', url);
            setPdfUrl(url);
            setLoadingProgress(100);
          } else {
            console.log('Request was cancelled, not setting PDF URL');
          }
        })
        .catch((err) => {
          console.log('downloadDocumentBlob promise rejected');
          if (!cancelled) {
            console.error('Failed to load PDF:', err);
            console.error('Error details:', {
              message: err.message,
              response: err.response?.data,
              status: err.response?.status,
              statusText: err.response?.statusText
            });
            setLoadingProgress(0);
          }
        });
    } else {
      console.log('Not loading PDF - id:', id, 'currentDocument:', currentDocument);
    }

    return () => {
      cancelled = true;
      if (pdfUrl) {
        console.log('Cleaning up blob URL:', pdfUrl);
        URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, currentDocument]);  const handleBack = () => {
    navigate('/documents');
  };

  const handleDownloadPDF = async () => {
    if (!id || !currentDocument) return;

    try {
      const blob = await documentService.downloadDocumentBlob(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = currentDocument.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF:', err);
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back
        </Button>
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">
            {error}
          </p>
        </div>
      </div>
    );
  }

  if (!currentDocument) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back
        </Button>
        <div className="text-center py-12">
          <p className="text-gray-600 dark:text-gray-400">Document not found</p>
        </div>
      </div>
    );
  }

  if (!pdfUrl) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back
        </Button>
        <div className="flex flex-col items-center justify-center py-12 gap-6">
          <Spinner size="lg" />
          <div className="w-full max-w-md space-y-2">
            <div className="flex items-center justify-between text-sm">
              <p className="text-gray-600 dark:text-gray-400">Loading PDF...</p>
              <p className="text-gray-600 dark:text-gray-400 font-semibold">{loadingProgress}%</p>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${loadingProgress}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
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
              {currentDocument.page_count || 0} pages  Uploaded {
                currentDocument.upload_date
                  ? new Date(currentDocument.upload_date).toLocaleDateString()
                  : currentDocument.uploaded_at
                    ? new Date(currentDocument.uploaded_at).toLocaleDateString()
                    : 'Unknown date'
              }
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleDownloadPDF}>
            <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
            Download PDF
          </Button>
        </div>
      </div>

      <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-lg overflow-hidden" style={{ height: 'calc(100vh - 250px)' }}>
        <iframe
          src={pdfUrl}
          className="w-full h-full border-0"
          title={currentDocument.filename}
        />
      </div>
    </div>
  );
}
