import Modal from './ui/Modal';
import Button from './ui/Button';
import { SparklesIcon } from '@heroicons/react/24/outline';

interface TutorialWelcomeModalProps {
  isOpen: boolean;
  onSkip: () => void;
  onStart: () => void;
}

export const TutorialWelcomeModal = ({ isOpen, onSkip, onStart }: TutorialWelcomeModalProps) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onSkip}
      title="Welcome to Artemis Insight"
      size="md"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onSkip}>
            Skip Tutorial
          </Button>
          <Button onClick={onStart}>
            Start Tour
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <SparklesIcon className="w-8 h-8 text-primary-600 dark:text-primary-400" />
          <p className="text-gray-600 dark:text-gray-300">
            Transform your documents into intelligent, structured summaries using AI.
          </p>
        </div>
        <p className="text-gray-600 dark:text-gray-300">
          Let's take a quick tour to get you started!
        </p>
      </div>
    </Modal>
  );
};
