import { useState, useEffect } from 'react';
import { Tab } from '@headlessui/react';
import { useSearchParams } from 'react-router-dom';
import { DocumentTextIcon, CloudArrowUpIcon, RectangleStackIcon } from '@heroicons/react/24/outline';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { DocumentList } from '../components/documents/DocumentList';
import { BulkUploadZone } from '../components/documents/BulkUploadZone';
import { UploadProgress } from '../components/documents/UploadProgress';
import { useDocumentStore } from '../stores/document.store';
import api from '../lib/api';
import { cn } from '../lib/utils';

export default function DocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedTab, setSelectedTab] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const { fetchDocuments } = useDocumentStore();

  // Check for tab query parameter on mount
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'upload') {
      setSelectedTab(1);
      // Clear the query parameter after setting the tab
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const handleUploadComplete = async () => {
    // Refresh the document list to ensure the new document appears
    await fetchDocuments();
    // Switch back to My Documents tab after successful upload
    setSelectedTab(0);
  };

  const handleBulkFilesSelected = (files: File[]) => {
    // Store files in state for upload
    setSelectedFiles(files);
  };

  const handleBulkUploadStart = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);

    try {
      // Get metadata from session storage
      const metadata = JSON.parse(sessionStorage.getItem('bulkUploadMetadata') || '{}');

      // Create FormData with files
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      // Add metadata
      if (metadata.collectionName) {
        formData.append('collection_name', metadata.collectionName);
      }
      if (metadata.projectName) {
        formData.append('project_name', metadata.projectName);
      }
      if (metadata.tags) {
        formData.append('tags', metadata.tags);
      }

      // Upload files
      const response = await api.post('/batch/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Set batch job ID to start tracking progress
      setBatchJobId(response.data.id);

      // Clear files and metadata
      setSelectedFiles([]);
      sessionStorage.removeItem('bulkUploadMetadata');

    } catch (error: any) {
      console.error('Bulk upload failed:', error);
      alert(error.response?.data?.detail || 'Failed to start bulk upload');
      setIsUploading(false);
    }
  };

  const handleBulkUploadComplete = async () => {
    setIsUploading(false);
    setBatchJobId(null);
    await fetchDocuments();
    setSelectedTab(0);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Documents
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Upload and manage your PDF documents
        </p>
      </div>

      <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
        <Tab.List className="flex space-x-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
          <Tab
            className={({ selected }) =>
              cn(
                'w-full rounded-md py-2.5 text-sm font-medium leading-5',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'transition-colors duration-150',
                selected
                  ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50'
              )
            }
          >
            <div className="flex items-center justify-center gap-2">
              <DocumentTextIcon className="h-5 w-5" />
              <span>My Documents</span>
            </div>
          </Tab>
          <Tab
            className={({ selected }) =>
              cn(
                'w-full rounded-md py-2.5 text-sm font-medium leading-5',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'transition-colors duration-150',
                selected
                  ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50'
              )
            }
          >
            <div className="flex items-center justify-center gap-2">
              <CloudArrowUpIcon className="h-5 w-5" />
              <span>Single Upload</span>
            </div>
          </Tab>
          <Tab
            className={({ selected }) =>
              cn(
                'w-full rounded-md py-2.5 text-sm font-medium leading-5',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'transition-colors duration-150',
                selected
                  ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50'
              )
            }
          >
            <div className="flex items-center justify-center gap-2">
              <RectangleStackIcon className="h-5 w-5" />
              <span>Bulk Upload</span>
            </div>
          </Tab>
        </Tab.List>

        <Tab.Panels className="mt-6">
          <Tab.Panel className="focus:outline-none">
            <DocumentList />
          </Tab.Panel>
          <Tab.Panel className="focus:outline-none">
            <DocumentUpload onUploadComplete={handleUploadComplete} />
          </Tab.Panel>
          <Tab.Panel className="focus:outline-none">
            <div className="space-y-6">
              {!isUploading && !batchJobId && (
                <BulkUploadZone
                  onFilesSelected={handleBulkFilesSelected}
                  onUploadStart={handleBulkUploadStart}
                  isUploading={isUploading}
                />
              )}
              {batchJobId && (
                <UploadProgress
                  jobId={batchJobId}
                  onComplete={handleBulkUploadComplete}
                />
              )}
            </div>
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
}
