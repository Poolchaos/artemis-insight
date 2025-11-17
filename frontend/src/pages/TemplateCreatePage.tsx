import { TemplateForm } from '../components/templates/TemplateForm';

export default function TemplateCreatePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Create Template
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Define a custom template for document summarization
        </p>
      </div>

      <TemplateForm mode="create" />
    </div>
  );
}
