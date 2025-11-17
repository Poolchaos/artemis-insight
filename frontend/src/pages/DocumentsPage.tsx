import { useState } from 'react';
import { Tab } from '@headlessui/react';
import { DocumentTextIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { DocumentList } from '../components/documents/DocumentList';
import { useDocumentStore } from '../stores/document.store';
import { cn } from '../lib/utils';

export default function DocumentsPage() {
  const [selectedTab, setSelectedTab] = useState(0);
  const { fetchDocuments } = useDocumentStore();

  const handleUploadComplete = async () => {
    // Refresh the document list to ensure the new document appears
    await fetchDocuments();
    // Switch back to My Documents tab after successful upload
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
              <span>Upload</span>
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
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
}
