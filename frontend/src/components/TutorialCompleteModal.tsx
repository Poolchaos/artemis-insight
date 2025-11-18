import Modal from './ui/Modal';
import Button from './ui/Button';
import { CheckCircleIcon } from '@heroicons/react/24/outline';

interface TutorialCompleteModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TutorialCompleteModal = ({ isOpen, onClose }: TutorialCompleteModalProps) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="You're All Set!"
      size="md"
      footer={
        <div className="flex justify-end">
          <Button onClick={onClose}>
            Get Started
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <CheckCircleIcon className="w-8 h-8 text-green-600 dark:text-green-400" />
          <p className="text-gray-600 dark:text-gray-300">
            You now know the basics of Artemis Insight.
          </p>
        </div>
        <p className="text-gray-600 dark:text-gray-300">
          Start by uploading a document and creating your first summary!
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          You can restart this tutorial anytime from your profile menu.
        </p>
      </div>
    </Modal>
  );
};
