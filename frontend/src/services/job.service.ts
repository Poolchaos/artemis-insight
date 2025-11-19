import api from '../lib/api';

export type JobType = 'upload' | 'extract' | 'summarize' | 'embed' | 'regenerate_section';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Job {
  id: string;
  user_id: string;
  document_id: string;
  template_id?: string;
  summary_id?: string;
  job_type: JobType;
  status: JobStatus;
  progress: number;
  error_message?: string;
  celery_task_id?: string;
  started_at: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export const jobService = {
  /**
   * Get job status
   */
  async getJob(jobId: string): Promise<Job> {
    const response = await api.get<Job>(`/api/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Poll job status until completion or failure
   * Returns the final job state
   */
  async pollJob(
    jobId: string,
    onProgress?: (job: Job) => void,
    pollInterval: number = 2000,
    timeout: number = 600000 // 10 minutes default (increased from 5)
  ): Promise<Job> {
    const startTime = Date.now();
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 3;
    let currentInterval = pollInterval;
    const maxInterval = 30000; // Max 30 seconds between polls

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          // Check timeout
          if (Date.now() - startTime > timeout) {
            reject(new Error('Job polling timeout - task may still be processing. Check job status later or contact support.'));
            return;
          }

          // Get job status
          const job = await this.getJob(jobId);

          // Reset error counter on success
          consecutiveErrors = 0;

          // Notify progress callback
          if (onProgress) {
            onProgress(job);
          }

          // Check if job is complete
          if (job.status === 'completed') {
            resolve(job);
            return;
          }

          if (job.status === 'failed') {
            reject(new Error(job.error_message || 'Job failed'));
            return;
          }

          if (job.status === 'cancelled') {
            reject(new Error('Job was cancelled'));
            return;
          }

          // Exponential backoff for long-running jobs
          // After 2 minutes, slow down polling to reduce server load
          const elapsed = Date.now() - startTime;
          if (elapsed > 120000) { // 2 minutes
            currentInterval = Math.min(currentInterval * 1.5, maxInterval);
          }

          // Continue polling
          setTimeout(poll, currentInterval);
        } catch (error) {
          consecutiveErrors++;

          // Circuit breaker: stop polling after too many errors
          if (consecutiveErrors >= maxConsecutiveErrors) {
            reject(new Error('Too many polling errors. Server may be overloaded. Please try again later.'));
            return;
          }

          // Exponential backoff on errors
          const errorBackoff = Math.min(pollInterval * Math.pow(2, consecutiveErrors), maxInterval);
          setTimeout(poll, errorBackoff);
        }
      };

      // Start polling
      poll();
    });
  },

  /**
   * Cancel a job
   */
  async cancelJob(jobId: string): Promise<void> {
    await api.post(`/api/jobs/${jobId}/cancel`);
  },

  /**
   * List jobs with optional filters
   */
  async listJobs(params?: {
    job_type?: JobType;
    status?: JobStatus;
    document_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<Job[]> {
    const response = await api.get<Job[]>('/api/jobs', { params });
    return response.data;
  },
};
