import { useEffect, useState } from 'react';
import Card from '../ui/Card';
import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import api from '../../lib/api';

interface BatchJobStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'partial';
  total_items: number;
  completed_items: number;
  failed_items: number;
  item_statuses: Array<{
    document_id: string;
    filename: string;
    status: string;
    error_message?: string;
  }>;
  collection_id?: string;
}

interface UploadProgressProps {
  jobId: string | null;
  onComplete: () => void;
}

export function UploadProgress({ jobId, onComplete }: UploadProgressProps) {
  const [jobStatus, setJobStatus] = useState<BatchJobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    // Poll for job status every 2 seconds
    const pollInterval = setInterval(async () => {
      try {
        const response = await api.get(`/batch/jobs/${jobId}`);
        const status: BatchJobStatus = response.data;
        setJobStatus(status);

        // Stop polling if job is complete
        if (
          status.status === 'completed' ||
          status.status === 'failed' ||
          status.status === 'partial'
        ) {
          clearInterval(pollInterval);
          setTimeout(() => {
            onComplete();
          }, 2000); // Show final status for 2 seconds before callback
        }
      } catch (err) {
        const error = err as { response?: { data?: { detail?: string } } };
        setError(error.response?.data?.detail || 'Failed to fetch job status');
        clearInterval(pollInterval);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId, onComplete]);

  if (!jobId || !jobStatus) {
    return null;
  }

  const progressPercentage = jobStatus.total_items > 0
    ? Math.round(((jobStatus.completed_items + jobStatus.failed_items) / jobStatus.total_items) * 100)
    : 0;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'text-gray-500';
      case 'processing':
        return 'text-blue-500';
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      case 'partial':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (itemStatus: string) => {
    if (itemStatus === 'success') {
      return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
    } else if (itemStatus === 'failed') {
      return <XCircleIcon className="w-5 h-5 text-red-500" />;
    }
    return <ClockIcon className="w-5 h-5 text-gray-400 animate-pulse" />;
  };

  return (
    <Card className="p-6">
      <div className="space-y-6">
        {/* Overall Progress */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Upload Progress
            </h3>
            <span className={`text-sm font-medium capitalize ${getStatusColor(jobStatus.status)}`}>
              {jobStatus.status}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2">
            <div
              className={`h-3 rounded-full transition-all duration-300 ${
                jobStatus.status === 'completed'
                  ? 'bg-green-500'
                  : jobStatus.status === 'failed'
                  ? 'bg-red-500'
                  : jobStatus.status === 'partial'
                  ? 'bg-yellow-500'
                  : 'bg-blue-500'
              }`}
              style={{ width: `${progressPercentage}%` }}
            />
          </div>

          {/* Stats */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              {jobStatus.completed_items + jobStatus.failed_items} of {jobStatus.total_items} processed
            </span>
            <span className="text-gray-600 dark:text-gray-400">
              {progressPercentage}%
            </span>
          </div>

          {jobStatus.failed_items > 0 && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              {jobStatus.failed_items} file{jobStatus.failed_items !== 1 ? 's' : ''} failed to upload
            </p>
          )}
        </div>

        {/* Individual File Status */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            File Status
          </h4>
          <div className="max-h-64 overflow-y-auto space-y-2">
            {jobStatus.item_statuses.map((item, index) => (
              <div
                key={`${item.filename}-${index}`}
                className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="shrink-0 mt-0.5">
                  {getStatusIcon(item.status)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {item.filename}
                  </p>
                  {item.error_message && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                      {item.error_message}
                    </p>
                  )}
                  {item.status === 'success' && item.document_id && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      ID: {item.document_id.substring(0, 8)}...
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Collection Created */}
        {jobStatus.collection_id && jobStatus.status === 'completed' && (
          <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-sm font-medium text-green-800 dark:text-green-300">
              Collection created successfully!
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              ID: {jobStatus.collection_id}
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
          </div>
        )}
      </div>
    </Card>
  );
}
