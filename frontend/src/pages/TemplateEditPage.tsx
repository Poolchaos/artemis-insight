import { useParams } from 'react-router-dom';
import { TemplateForm } from '../components/templates/TemplateForm';

export default function TemplateEditPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Edit Template
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Update your template configuration
        </p>
      </div>

      <TemplateForm mode="edit" templateId={id} />
    </div>
  );
}
