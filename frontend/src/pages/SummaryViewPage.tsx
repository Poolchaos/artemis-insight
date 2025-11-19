import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DocumentTextIcon, DocumentDuplicateIcon, ArrowDownTrayIcon, TrashIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';
import Button from '../components/ui/Button';
import Card, { CardContent } from '../components/ui/Card';
import Modal from '../components/ui/Modal';
import { MarkdownContent } from '../components/ui/MarkdownContent';
import { summaryService } from '../services/summary.service';
import { jobService, type Job } from '../services/job.service';
import type { Summary } from '../types';

export default function SummaryViewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [showRetryModal, setShowRetryModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [retryStage, setRetryStage] = useState<string>('');

  const fetchSummary = async () => {
    if (!id) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await summaryService.getSummaryById(id);
      setSummary(data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(error?.response?.data?.detail || error?.message || 'Failed to load summary');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchSummary();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    const handleClickOutside = () => {
      if (showExportMenu) {
        setShowExportMenu(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showExportMenu]);

  const handleExport = async (format: 'pdf' | 'docx') => {
    if (!id) return;

    setIsExporting(true);
    setShowExportMenu(false);

    try {
      await summaryService.exportSummary(id, format);
    } catch (err) {
      console.error('Failed to export summary:', err);
      setErrorMessage('Failed to export summary. Please try again.');
      setShowErrorModal(true);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirm = async () => {
    if (!id) return;

    setShowDeleteConfirm(false);
    setIsDeleting(true);

    try {
      await summaryService.deleteSummary(id);
      navigate('/summaries');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setErrorMessage(error?.response?.data?.detail || error?.message || 'Failed to delete summary');
      setShowErrorModal(true);
      setIsDeleting(false);
    }
  };

  const getRetryStageMessage = (job: Job | null): string => {
    if (!job) return 'Starting retry...';
    if (job.status === 'pending') return 'Preparing document...';
    if (job.status === 'running') {
      if (job.progress < 20) return 'Reading document...';
      if (job.progress < 40) return 'Extracting content...';
      if (job.progress < 60) return 'Analyzing with AI...';
      if (job.progress < 80) return 'Generating summary...';
      if (job.progress < 100) return 'Finalizing...';
    }
    return 'Processing...';
  };

  const handleRetry = async () => {
    if (!id) return;

    setIsRetrying(true);
    setShowRetryModal(true);
    setCurrentJob(null);
    setRetryStage('Starting retry...');

    try {
      // Start retry
      const result = await summaryService.retrySummary(id);

      // Poll the new job
      const finalJob = await jobService.pollJob(
        result.job_id,
        (job) => {
          setCurrentJob(job);
          setRetryStage(getRetryStageMessage(job));
        },
        2000,
        600000 // 10 minutes
      );

      // Success! Redirect to new summary
      if (finalJob.summary_id) {
        setShowRetryModal(false);
        navigate(`/summaries/${finalJob.summary_id}`);
        // Refresh to show new summary
        window.location.reload();
      } else {
        setErrorMessage('Retry completed but no summary was generated.');
        setShowErrorModal(true);
        setShowRetryModal(false);
      }
    } catch (err: unknown) {
      console.error('Retry failed:', err);
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setErrorMessage(error?.response?.data?.detail || error?.message || 'Failed to retry summary generation');
      setShowErrorModal(true);
      setShowRetryModal(false);
    } finally {
      setIsRetrying(false);
      setCurrentJob(null);
      setRetryStage('');
    }
  };

  const formatProcessingTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    const parts: string[] = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

    return parts.join(' ');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="relative w-16 h-16 mb-4 mx-auto">
            <div className="absolute inset-0 border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <p className="text-gray-600 dark:text-gray-400">Loading summary...</p>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <Card>
          <CardContent className="p-8 text-center">
            <XCircleIcon className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Failed to Load Summary
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {error || 'Summary not found'}
            </p>
            <Button onClick={() => navigate('/process')}>
              Back to Process
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusColors = {
    processing: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
    completed: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20',
    failed: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <DocumentTextIcon className="h-8 w-8 text-blue-500" />
            Document Summary
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Generated using {summary.template_name}
          </p>
        </div>
        <div className="flex gap-2">
          {summary.status === 'failed' && (
            <Button
              onClick={handleRetry}
              disabled={isRetrying}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isRetrying ? (
                <>
                  <div className="w-5 h-5 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <ArrowPathIcon className="h-5 w-5 mr-2" />
                  Retry
                </>
              )}
            </Button>
          )}
          {summary.status === 'completed' && (
            <div className="relative">
              <Button
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowExportMenu(!showExportMenu);
                }}
                disabled={isExporting}
              >
                {isExporting ? (
                  <>
                    <div className="w-5 h-5 mr-2 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
                    Export
                  </>
                )}
              </Button>
              {showExportMenu && !isExporting && (
                <div
                className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => handleExport('pdf')}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-t-md"
                >
                  Export as PDF
                </button>
                <button
                  onClick={() => handleExport('docx')}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-b-md"
                >
                  Export as Word (DOCX)
                </button>
              </div>
            )}
            </div>
          )}
          <Button
            variant="outline"
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            {isDeleting ? (
              <>
                <div className="w-5 h-5 mr-2 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <TrashIcon className="h-5 w-5 mr-2" />
                Delete
              </>
            )}
          </Button>
          <Button variant="outline" onClick={() => navigate('/summaries')}>
            Back
          </Button>
        </div>
      </div>

      {/* Metadata Card */}
      <Card>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Status</div>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[summary.status]}`}>
                {summary.status === 'completed' && <CheckCircleIcon className="h-4 w-4 mr-1" />}
                {summary.status === 'failed' && <XCircleIcon className="h-4 w-4 mr-1" />}
                {summary.status.toUpperCase()}
              </span>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Sections</div>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {summary.sections.length}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Words</div>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {summary.sections.reduce((sum, s) => sum + s.word_count, 0).toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Processing Time</div>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {summary.metadata?.processing_duration_seconds
                  ? formatProcessingTime(summary.metadata.processing_duration_seconds)
                  : 'N/A'}
              </div>
            </div>
          </div>

          {summary.metadata && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Pages:</span>
                  <span className="ml-2 text-gray-900 dark:text-gray-100">{summary.metadata.total_pages}</span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Source Words:</span>
                  <span className="ml-2 text-gray-900 dark:text-gray-100">{summary.metadata.total_words.toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Error Message Card for Failed Summaries */}
      {summary.status === 'failed' && summary.error_message && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-start gap-3">
              <XCircleIcon className="h-6 w-6 text-red-500 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
                  Processing Failed
                </h3>
                <p className="text-gray-700 dark:text-gray-300 mb-4">
                  {summary.error_message}
                </p>
                <Button
                  onClick={handleRetry}
                  disabled={isRetrying}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {isRetrying ? (
                    <>
                      <div className="w-5 h-5 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Retrying...
                    </>
                  ) : (
                    <>
                      <ArrowPathIcon className="h-5 w-5 mr-2" />
                      Retry Now
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sections */}
      <div className="space-y-4">
        {summary.sections
          .sort((a, b) => a.order - b.order)
          .map((section, index) => (
            <Card key={index}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {section.order}. {section.title}
                  </h2>
                  <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <DocumentDuplicateIcon className="h-4 w-4" />
                      {section.word_count} words
                    </div>
                  </div>
                </div>

                <MarkdownContent
                  content={section.content}
                  className="text-gray-700 dark:text-gray-300"
                />

                {section.pages_referenced.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      <span className="font-medium">Referenced pages:</span>
                      <span className="ml-2">{section.pages_referenced.join(', ')}</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Delete Summary"
        size="sm"
        footer={
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setShowDeleteConfirm(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Delete
            </Button>
          </div>
        }
      >
        <p className="text-gray-700 dark:text-gray-300">
          Are you sure you want to delete this summary? This action cannot be undone.
        </p>
      </Modal>

      {/* Error Modal */}
      <Modal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title="Error"
        size="sm"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setShowErrorModal(false)}>
              OK
            </Button>
          </div>
        }
      >
        <p className="text-gray-700 dark:text-gray-300">
          {errorMessage}
        </p>
      </Modal>

      {/* Retry Progress Modal */}
      <Modal
        isOpen={showRetryModal}
        onClose={() => {}} // Prevent closing during retry
        title="Retrying Summary Generation"
      >
        <div className="flex flex-col items-center justify-center py-4">
          {/* Animated spinner */}
          <div className="relative w-20 h-20 mb-6">
            <div className="absolute inset-0 border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
            {/* Progress percentage in center */}
            {currentJob && (
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  {currentJob.progress}%
                </span>
              </div>
            )}
          </div>

          {/* Stage message */}
          <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
            {retryStage}
          </p>

          {/* Progress bar */}
          {currentJob && (
            <div className="w-full">
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${currentJob.progress}%` }}
                />
              </div>

              {/* Job details */}
              <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center space-y-1">
                <div>Status: <span className="font-medium">{currentJob.status}</span></div>
                <div>Retrying with improved error handling...</div>
              </div>
            </div>
          )}

          {/* Cancel button */}
          <div className="mt-6">
            <Button
              variant="outline"
              onClick={async () => {
                if (currentJob) {
                  try {
                    await jobService.cancelJob(currentJob.id);
                  } catch (error) {
                    console.error('Failed to cancel job:', error);
                  }
                }
                setIsRetrying(false);
                setShowRetryModal(false);
                setCurrentJob(null);
              }}
              size="sm"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
