import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { summaryService } from '../services/summary.service';
import { type SummaryListItem } from '../types';
import Modal from '../components/ui/Modal';
import Button from '../components/ui/Button';
import {
  DocumentCheckIcon,
  ClockIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

export default function SummariesPage() {
  const navigate = useNavigate();
  const [summaries, setSummaries] = useState<SummaryListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'processing' | 'completed' | 'failed'>('all');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchSummaries = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = filter !== 'all' ? { status: filter } : undefined;
      const data = await summaryService.listSummaries(params);
      setSummaries(data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(error?.response?.data?.detail || error?.message || 'Failed to load summaries');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSummaries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const handleDeleteClick = (summaryId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent navigation when clicking delete
    setDeleteTargetId(summaryId);
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTargetId) return;

    setShowDeleteConfirm(false);
    setDeletingId(deleteTargetId);

    try {
      await summaryService.deleteSummary(deleteTargetId);
      // Remove from local state
      setSummaries(summaries.filter(s => s.id !== deleteTargetId));
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setErrorMessage(error?.response?.data?.detail || error?.message || 'Failed to delete summary');
      setShowErrorModal(true);
    } finally {
      setDeletingId(null);
      setDeleteTargetId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
            <CheckCircleIcon className="w-4 h-4 mr-1" />
            Completed
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            <ArrowPathIcon className="w-4 h-4 mr-1 animate-spin" />
            Processing
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
            <ExclamationCircleIcon className="w-4 h-4 mr-1" />
            Failed
          </span>
        );
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  const formatDuration = (startedAt: string, completedAt?: string) => {
    if (!completedAt) return 'In progress...';

    const start = new Date(startedAt);
    const end = new Date(completedAt);
    const durationMs = end.getTime() - start.getTime();
    const durationSeconds = Math.floor(durationMs / 1000);

    if (durationSeconds < 60) return `${durationSeconds}s`;
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    return `${minutes}m ${seconds}s`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <ExclamationCircleIcon className="w-16 h-16 text-red-500 mb-4" />
        <p className="text-red-600 dark:text-red-400 text-lg mb-4">{error}</p>
        <button
          onClick={fetchSummaries}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Summaries</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            View and manage your generated document summaries
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            filter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('completed')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            filter === 'completed'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          Completed
        </button>
        <button
          onClick={() => setFilter('processing')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            filter === 'processing'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          Processing
        </button>
        <button
          onClick={() => setFilter('failed')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            filter === 'failed'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          Failed
        </button>
      </div>

      {/* Empty State */}
      {summaries.length === 0 && (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <DocumentCheckIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">No summaries</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {filter === 'all'
              ? 'Get started by generating a summary from the Process page.'
              : `No ${filter} summaries found.`}
          </p>
          {filter === 'all' && (
            <div className="mt-6">
              <button
                onClick={() => navigate('/process')}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Generate Summary
              </button>
            </div>
          )}
        </div>
      )}

      {/* Summaries List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {summaries.map((summary) => (
          <div
            key={summary.id}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow relative"
          >
            {/* Delete Button */}
            <button
              onClick={(e) => handleDeleteClick(summary.id, e)}
              disabled={deletingId === summary.id}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
              title="Delete summary"
            >
              {deletingId === summary.id ? (
                <div className="w-5 h-5 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
              ) : (
                <TrashIcon className="w-5 h-5" />
              )}
            </button>

            {/* Clickable area to navigate */}
            <div
              onClick={() => navigate(`/summaries/${summary.id}`)}
              className="cursor-pointer"
            >
              {/* Status Badge */}
              <div className="flex items-start justify-between mb-4 pr-8">
                {getStatusBadge(summary.status)}
                <ClockIcon className="w-5 h-5 text-gray-400" />
              </div>

              {/* Template Name */}
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                {summary.template_name}
              </h3>

              {/* Stats */}
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-center">
                  <DocumentTextIcon className="w-4 h-4 mr-2" />
                  <span>{summary.section_count} sections</span>
                </div>
                <div className="flex items-center">
                  <DocumentCheckIcon className="w-4 h-4 mr-2" />
                  <span>{summary.total_word_count.toLocaleString()} words</span>
                </div>
              </div>

              {/* Dates */}
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  <div>Started: {formatDate(summary.started_at)}</div>
                  {summary.completed_at && (
                    <div className="mt-1">
                      Completed in {formatDuration(summary.started_at, summary.completed_at)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
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
    </div>
  );
}
