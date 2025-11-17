import { TemplateList } from '../components/templates/TemplateList';

export default function TemplatesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Templates
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Create and manage document summarization templates
        </p>
      </div>

      <TemplateList />
    </div>
  );
}
