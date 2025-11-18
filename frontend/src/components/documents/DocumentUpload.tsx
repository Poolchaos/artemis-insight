import { useState, useCallback } from 'react';
import { CloudArrowUpIcon, DocumentTextIcon, XMarkIcon } from '@heroicons/react/24/outline';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import { useDocumentStore } from '../../stores/document.store';

interface DocumentUploadProps {
  onUploadComplete?: (documentId: string) => void;
}

export function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showProcessingModal, setShowProcessingModal] = useState(false);
  const [uploadedFilename, setUploadedFilename] = useState('');

  const { uploadDocument, isLoading, error, clearError } = useDocumentStore();

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(file => file.type === 'application/pdf');

    if (pdfFile) {
      setSelectedFile(pdfFile);
      clearError();
    }
  }, [clearError]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      clearError();
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      const filename = selectedFile.name;
      const document = await uploadDocument(selectedFile);

      setSelectedFile(null);
      setUploadedFilename(filename);
      setShowProcessingModal(true);

      if (onUploadComplete) {
        onUploadComplete(document.id);
      }
    } catch {
      // Error is handled by the store
    }
  };

  return (
    <div className="space-y-6">
      {/* Drag and Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        data-tour="upload-button"
        className={`
          relative border-2 border-dashed rounded-lg p-12 text-center
          transition-colors duration-200
          ${isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }
        `}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileSelect}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isLoading}
        />

        <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />

        <div className="mt-4">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {isDragging ? 'Drop your PDF here' : 'Drag and drop your PDF here'}
          </p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            or click to browse
          </p>
        </div>

        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Only PDF files are supported
        </p>
      </div>

      {/* Selected File */}
      {selectedFile && (
        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="flex items-center space-x-3">
            <DocumentTextIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          </div>

          {!isLoading && (
            <button
              onClick={handleRemoveFile}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Upload Button */}
      {selectedFile && (
        <div className="flex justify-end">
          <Button
            onClick={handleUpload}
            disabled={isLoading}
            isLoading={isLoading}
          >
            {isLoading ? 'Uploading...' : 'Upload Document'}
          </Button>
        </div>
      )}

      {/* Processing Modal */}
      <Modal
        isOpen={showProcessingModal}
        onClose={() => setShowProcessingModal(false)}
        title="Document Processing"
        footer={
          <div className="flex justify-end">
            <Button onClick={() => setShowProcessingModal(false)}>
              Got it
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="flex items-center justify-center">
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
            </div>
          </div>

          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Your document is being processed
            </h3>
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              <strong>{uploadedFilename}</strong> has been uploaded successfully and is now being processed.
            </p>
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-sm text-left">
              <p className="text-gray-700 dark:text-gray-300 mb-2">
                <strong>What happens next?</strong>
              </p>
              <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
                <li>OCR and text extraction (~2-5 seconds)</li>
                <li>Document will be ready for analysis</li>
                <li>You'll see it in your documents list shortly</li>
              </ul>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
              You can close this and continue working. The document will appear in your list once processing is complete.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
