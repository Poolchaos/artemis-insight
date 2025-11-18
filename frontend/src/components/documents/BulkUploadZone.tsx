import Card from '../ui/Card';
import Button from '../ui/Button';
import { CloudArrowUpIcon, XMarkIcon, DocumentIcon } from '@heroicons/react/24/outline';
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface BulkUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  onUploadStart: () => void;
  isUploading?: boolean;
}

interface FileWithPreview extends File {
  preview?: string;
}

export function BulkUploadZone({ onFilesSelected, onUploadStart, isUploading = false }: BulkUploadZoneProps) {
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);
  const [collectionName, setCollectionName] = useState('');
  const [projectName, setProjectName] = useState('');
  const [tags, setTags] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.filter(file => {
      // Check if file already exists
      return !selectedFiles.some(existing => existing.name === file.name);
    });

    setSelectedFiles(prev => [...prev, ...newFiles]);
  }, [selectedFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: true,
    maxFiles: 50,
    disabled: isUploading
  });

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setSelectedFiles([]);
    setCollectionName('');
    setProjectName('');
    setTags('');
  };

  const handleUpload = () => {
    if (selectedFiles.length === 0) return;

    // Pass metadata along with files
    const metadata = {
      collectionName: collectionName.trim() || undefined,
      projectName: projectName.trim() || undefined,
      tags: tags.trim() || undefined
    };

    onFilesSelected(selectedFiles);
    onUploadStart();

    // Store metadata for the upload request
    sessionStorage.setItem('bulkUploadMetadata', JSON.stringify(metadata));
  };

  const totalSize = selectedFiles.reduce((acc, file) => acc + file.size, 0);
  const formattedSize = (totalSize / (1024 * 1024)).toFixed(2);

  return (
    <Card className="p-6">
      <div className="space-y-6">
        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
            ${isDragActive ? 'border-primary-500 bg-primary-50 dark:bg-primary-950' : 'border-gray-300 dark:border-gray-600'}
            ${isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary-400 dark:hover:border-primary-500'}
          `}
        >
          <input {...getInputProps()} />
          <CloudArrowUpIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          {isDragActive ? (
            <p className="text-lg font-medium text-primary-600 dark:text-primary-400">
              Drop files here...
            </p>
          ) : (
            <>
              <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Drop PDF files here, or click to select
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Upload up to 50 PDF files at once
              </p>
            </>
          )}
        </div>

        {/* Selected Files List */}
        {selectedFiles.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Selected Files ({selectedFiles.length})
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Total: {formattedSize} MB
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  disabled={isUploading}
                >
                  Clear All
                </Button>
              </div>
            </div>

            <div className="max-h-64 overflow-y-auto space-y-2">
              {selectedFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <DocumentIcon className="w-5 h-5 text-gray-400 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  {!isUploading && (
                    <button
                      onClick={() => removeFile(index)}
                      className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    >
                      <XMarkIcon className="w-5 h-5 text-gray-400" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Metadata Inputs */}
            <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div>
                <label htmlFor="collectionName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Collection Name (Optional)
                </label>
                <input
                  id="collectionName"
                  type="text"
                  value={collectionName}
                  onChange={(e) => setCollectionName(e.target.value)}
                  placeholder="e.g., Bridge Construction Phase 1"
                  disabled={isUploading}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Group these documents into a named collection
                </p>
              </div>

              <div>
                <label htmlFor="projectName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Project Name (Optional)
                </label>
                <input
                  id="projectName"
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g., Highway 101 Expansion"
                  disabled={isUploading}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                />
              </div>

              <div>
                <label htmlFor="tags" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Tags (Optional)
                </label>
                <input
                  id="tags"
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="e.g., structural, engineering, phase-1"
                  disabled={isUploading}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Comma-separated tags for all documents
                </p>
              </div>
            </div>

            {/* Upload Button */}
            <Button
              onClick={handleUpload}
              disabled={isUploading || selectedFiles.length === 0}
              className="w-full"
              size="lg"
            >
              {isUploading ? 'Uploading...' : `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
