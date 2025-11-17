import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SparklesIcon, DocumentTextIcon, BeakerIcon } from '@heroicons/react/24/outline';
import Button from '../components/ui/Button';
import Card, { CardContent } from '../components/ui/Card';
import Modal from '../components/ui/Modal';
import { useDocumentStore } from '../stores/document.store';
import { useTemplateStore } from '../stores/template.store';
import { summaryService } from '../services/summary.service';
import { jobService, type Job } from '../services/job.service';

export default function ProcessPage() {
  const navigate = useNavigate();
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [processingStage, setProcessingStage] = useState<string>('');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<{
    title: string;
    message: string;
    isError: boolean;
    summaryId?: string;
  }>({ title: '', message: '', isError: false });

  const { documents, fetchDocuments } = useDocumentStore();
  const { templates, fetchTemplates } = useTemplateStore();

  useEffect(() => {
    fetchDocuments();
    fetchTemplates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedDocument = documents?.find(d => d.id === selectedDocumentId);
  const selectedTemplate = templates?.find(t => t.id === selectedTemplateId);

  const canProcess = selectedDocumentId && selectedTemplateId && selectedDocument?.status === 'completed';

  const getProcessingStageMessage = (job: Job | null): string => {
    if (!job) return 'Starting...';

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

  const handleProcess = async () => {
    if (!canProcess) return;

    setIsProcessing(true);
    setCurrentJob(null);
    setProcessingStage('Starting...');

    try {
      // Create summary job via API
      const result = await summaryService.createSummary(selectedDocumentId, selectedTemplateId);

      // Start polling the job status
      const finalJob = await jobService.pollJob(
        result.job_id,
        (job) => {
          // Update UI with progress
          setCurrentJob(job);
          setProcessingStage(getProcessingStageMessage(job));
        },
        2000, // Poll every 2 seconds
        300000 // 5 minute timeout
      );

      // Job completed successfully! Show success modal
      if (finalJob.summary_id) {
        setModalContent({
          title: 'Summary Generated Successfully!',
          message: 'Your document has been processed and the summary is ready to view.',
          isError: false,
          summaryId: finalJob.summary_id
        });
        setIsModalOpen(true);
      } else {
        // Show error if no summary ID (shouldn't happen)
        setModalContent({
          title: 'Processing Error',
          message: 'Processing completed but no summary was generated.',
          isError: true
        });
        setIsModalOpen(true);
      }

      // Reset selections
      setSelectedDocumentId('');
      setSelectedTemplateId('');
    } catch (error: unknown) {
      console.error('Processing failed:', error);

      // Extract error message from response
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage = err?.response?.data?.detail
        || err?.message
        || 'Failed to process document. Please try again.';

      // Show error modal with detailed message
      setModalContent({
        title: 'Processing Failed',
        message: errorMessage,
        isError: true
      });
      setIsModalOpen(true);
    } finally {
      setIsProcessing(false);
      setCurrentJob(null);
      setProcessingStage('');
    }
  };  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <SparklesIcon className="h-8 w-8 text-blue-500" />
          Process Document
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Select a document and template to generate an AI-powered summary
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Document Selection */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <DocumentTextIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Select Document
              </h2>
            </div>

            {(!documents || documents.length === 0) ? (
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  No documents uploaded yet
                </p>
                <Button onClick={() => navigate('/documents')}>
                  Upload Document
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => {
                  const statusColors = {
                    pending: 'text-yellow-600 dark:text-yellow-400',
                    processing: 'text-blue-600 dark:text-blue-400',
                    completed: 'text-green-600 dark:text-green-400',
                    failed: 'text-red-600 dark:text-red-400'
                  };

                  return (
                    <button
                      key={doc.id}
                      onClick={() => setSelectedDocumentId(doc.id)}
                      disabled={doc.status !== 'completed'}
                      className={`
                        w-full p-4 rounded-lg border-2 text-left transition-all
                        ${doc.status !== 'completed' ? 'opacity-50 cursor-not-allowed' : ''}
                        ${selectedDocumentId === doc.id
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }
                      `}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                            {doc.filename}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {doc.upload_date
                              ? new Date(doc.upload_date).toLocaleDateString()
                              : doc.uploaded_at
                                ? new Date(doc.uploaded_at).toLocaleDateString()
                                : 'Unknown date'
                            }
                          </div>
                        </div>
                        <div className="ml-4">
                          <span className={`text-xs font-medium px-2 py-1 rounded ${statusColors[(doc.status || 'pending') as keyof typeof statusColors]}`}>
                            {(doc.status || 'pending').toUpperCase()}
                          </span>
                        </div>
                      </div>
                      {doc.status !== 'completed' && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                          {doc.status === 'pending' && 'Document is awaiting processing'}
                          {doc.status === 'processing' && 'Document is being processed...'}
                          {doc.status === 'failed' && 'Document processing failed'}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Template Selection */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <BeakerIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Select Template
              </h2>
            </div>

            {(!templates || templates.length === 0) ? (
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  No templates available
                </p>
                <Button onClick={() => navigate('/templates')}>
                  Create Template
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplateId(template.id)}
                    className={`
                      w-full p-4 rounded-lg border-2 text-left transition-all
                      ${selectedTemplateId === template.id
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }
                    `}
                  >
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {template.name}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                      {template.description}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Selected Summary & Action */}
      {canProcess && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Ready to Analyze
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Document</div>
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {selectedDocument?.filename}
                </div>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Template</div>
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {selectedTemplate?.name}
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleProcess}
                disabled={isProcessing}
                isLoading={isProcessing}
                size="lg"
              >
                <SparklesIcon className="h-5 w-5 mr-2" />
                {isProcessing ? 'Processing...' : 'Generate Summary'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Processing Indicator with Real-time Progress */}
      {isProcessing && (
        <Card>
          <CardContent className="p-8">
            <div className="flex flex-col items-center justify-center">
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

              {/* Progress title */}
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Analyzing Document
              </h3>

              {/* Stage message */}
              <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
                {processingStage}
              </p>

              {/* Progress bar */}
              {currentJob && (
                <div className="w-full max-w-md">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${currentJob.progress}%` }}
                    />
                  </div>

                  {/* Job details */}
                  <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center space-y-1">
                    <div>Status: <span className="font-medium">{currentJob.status}</span></div>
                    <div>Document: <span className="font-medium">{selectedDocument?.filename}</span></div>
                    <div>Template: <span className="font-medium">{selectedTemplate?.name}</span></div>
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
                    setIsProcessing(false);
                    setCurrentJob(null);
                  }}
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Result Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={modalContent.title}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>
              Close
            </Button>
            {modalContent.summaryId && (
              <Button onClick={() => {
                setIsModalOpen(false);
                navigate(`/summaries/${modalContent.summaryId}`);
              }}>
                View Summary
              </Button>
            )}
          </div>
        }
      >
        <div className={modalContent.isError ? 'text-red-600 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'}>
          <p className="whitespace-pre-wrap">{modalContent.message}</p>
        </div>
      </Modal>
    </div>
  );
}
