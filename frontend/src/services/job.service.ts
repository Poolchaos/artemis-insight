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
    timeout: number = 300000 // 5 minutes default
  ): Promise<Job> {
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          // Check timeout
          if (Date.now() - startTime > timeout) {
            reject(new Error('Job polling timeout'));
            return;
          }

          // Get job status
          const job = await this.getJob(jobId);

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

          // Continue polling
          setTimeout(poll, pollInterval);
        } catch (error) {
          reject(error);
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
