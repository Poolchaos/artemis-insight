import React, { createContext, useContext, useState } from 'react';
import Shepherd from 'shepherd.js';
import 'shepherd.js/dist/css/shepherd.css';
import '../styles/shepherd-theme.css';
import {
  SparklesIcon,
  RectangleStackIcon,
  DocumentTextIcon,
  CloudArrowUpIcon,
  DocumentCheckIcon
} from '@heroicons/react/24/outline';
import { renderToStaticMarkup } from 'react-dom/server';
import { TutorialWelcomeModal } from '../components/TutorialWelcomeModal';
import { TutorialCompleteModal } from '../components/TutorialCompleteModal';

interface TutorialContextType {
  startTutorial: (navigateFn: (path: string) => void) => void;
  resetTutorial: (navigateFn: (path: string) => void) => void;
  isTutorialActive: boolean;
  showWelcomeModal: boolean;
  showCompleteModal: boolean;
  handleWelcomeStart: () => void;
  handleWelcomeSkip: () => void;
  handleCompleteClose: () => void;
}

const TutorialContext = createContext<TutorialContextType | undefined>(undefined);

export const useTutorial = () => {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error('useTutorial must be used within TutorialProvider');
  }
  return context;
};

// Helper to render icon as HTML string
const iconToHtml = (IconComponent: React.ComponentType<{ className?: string }>) => {
  return renderToStaticMarkup(<IconComponent className="w-6 h-6" />);
};

export const TutorialProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isTutorialActive, setIsTutorialActive] = useState(false);
  const [showWelcomeModal, setShowWelcomeModal] = useState(false);
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [navigateFunction, setNavigateFunction] = useState<((path: string) => void) | null>(null);

  const TUTORIAL_COMPLETED_KEY = 'artemis-tutorial-completed';

  const startTutorial = (navigateFn: (path: string) => void) => {
    setNavigateFunction(() => navigateFn);
    setShowWelcomeModal(true);
  };

  const handleWelcomeSkip = () => {
    localStorage.setItem(TUTORIAL_COMPLETED_KEY, 'true');
    setShowWelcomeModal(false);
    setIsTutorialActive(false);
  };

  const handleWelcomeStart = () => {
    setShowWelcomeModal(false);
    setIsTutorialActive(true);
    // Delay to prevent modal flicker
    setTimeout(() => {
      startGuidedTour();
    }, 100);
  };

  const handleCompleteClose = () => {
    localStorage.setItem(TUTORIAL_COMPLETED_KEY, 'true');
    setShowCompleteModal(false);
    setIsTutorialActive(false);
    if (navigateFunction) {
      navigateFunction('/dashboard');
    }
  };

  const startGuidedTour = () => {
    if (!navigateFunction) return;

    const tour = new Shepherd.Tour({
      useModalOverlay: true,
      defaultStepOptions: {
        cancelIcon: {
          enabled: true
        },
        classes: 'shepherd-theme-custom',
        scrollTo: { behavior: 'smooth', block: 'center' }
      }
    });

    // Step 1: Templates Navigation
    tour.addStep({
      id: 'templates-nav',
      title: `<div class="flex items-center gap-2">${iconToHtml(RectangleStackIcon)}<span>Templates</span></div>`,
      text: `
        <p class="text-gray-600 dark:text-gray-300">
          Templates define the structure of your summaries. Click here to explore pre-built templates or create your own.
        </p>
      `,
      attachTo: {
        element: '[data-tour="templates-nav"]',
        on: 'bottom'
      },
      buttons: [
        {
          text: 'Exit',
          classes: 'shepherd-button-secondary',
          action: () => {
            tour.cancel();
          }
        },
        {
          text: 'Next',
          action: () => {
            navigateFunction('/templates');
            setTimeout(() => tour.next(), 500);
          }
        }
      ]
    });

    // Step 2: Template List
    tour.addStep({
      id: 'template-list',
      title: 'Template Library',
      text: `
        <p class="text-gray-600 dark:text-gray-300">
          Browse existing templates or create custom ones. Each template contains sections that guide the AI in generating your summary.
        </p>
      `,
      attachTo: {
        element: '[data-tour="template-list"]',
        on: 'top'
      },
      buttons: [
        {
          text: 'Back',
          classes: 'shepherd-button-secondary',
          action: tour.back
        },
        {
          text: 'Next',
          action: tour.next
        }
      ]
    });

    // Step 3: Documents Navigation
    tour.addStep({
      id: 'documents-nav',
      title: `<div class="flex items-center gap-2">${iconToHtml(DocumentTextIcon)}<span>Documents</span></div>`,
      text: `
        <p class="text-gray-600 dark:text-gray-300">
          Upload and manage your PDF documents here. Let's check it out!
        </p>
      `,
      attachTo: {
        element: '[data-tour="documents-nav"]',
        on: 'bottom'
      },
      buttons: [
        {
          text: 'Back',
          classes: 'shepherd-button-secondary',
          action: tour.back
        },
        {
          text: 'Next',
          action: () => {
            navigateFunction('/documents');
            setTimeout(() => tour.next(), 500);
          }
        }
      ]
    });

    // Step 4: Upload Document
    tour.addStep({
      id: 'upload-document',
      title: `<div class="flex items-center gap-2">${iconToHtml(CloudArrowUpIcon)}<span>Upload Documents</span></div>`,
      text: `
        <p class="text-gray-600 dark:text-gray-300">
          Click here to upload PDF documents. Supported formats: PDF (up to 50MB)
        </p>
      `,
      attachTo: {
        element: '[data-tour="upload-button"]',
        on: 'left'
      },
      buttons: [
        {
          text: 'Back',
          classes: 'shepherd-button-secondary',
          action: tour.back
        },
        {
          text: 'Next',
          action: tour.next
        }
      ]
    });

    // Step 5: Process Navigation
    tour.addStep({
      id: 'process-nav',
      title: `<div class="flex items-center gap-2">${iconToHtml(SparklesIcon)}<span>Generate Summary</span></div>`,
      text: `
        <p class="text-gray-600 dark:text-gray-300">
          Once you've uploaded a document, come here to generate an AI-powered summary using your chosen template.
        </p>
      `,
      attachTo: {
        element: '[data-tour="process-nav"]',
        on: 'bottom'
      },
      buttons: [
        {
          text: 'Back',
          classes: 'shepherd-button-secondary',
          action: tour.back
        },
        {
          text: 'Next',
          action: tour.next
        }
      ]
    });

    // Step 6: Summaries Navigation
    tour.addStep({
      id: 'summaries-nav',
      title: `<div class="flex items-center gap-2">${iconToHtml(DocumentCheckIcon)}<span>View Summaries</span></div>`,
      text: `
        <p class="text-gray-600 dark:text-gray-300">
          Access all your generated summaries here. Review, search, and export your AI-generated content.
        </p>
      `,
      attachTo: {
        element: '[data-tour="summaries-nav"]',
        on: 'bottom'
      },
      buttons: [
        {
          text: 'Back',
          classes: 'shepherd-button-secondary',
          action: tour.back
        },
        {
          text: 'Finish',
          action: () => {
            tour.complete();
          }
        }
      ]
    });

    tour.on('complete', () => {
      setIsTutorialActive(false);
      setShowCompleteModal(true);
    });

    tour.on('cancel', () => {
      setIsTutorialActive(false);
    });

    tour.start();
  };

  const resetTutorial = (navigateFn: (path: string) => void) => {
    localStorage.removeItem(TUTORIAL_COMPLETED_KEY);
    startTutorial(navigateFn);
  };

  return (
    <TutorialContext.Provider
      value={{
        startTutorial,
        resetTutorial,
        isTutorialActive,
        showWelcomeModal,
        showCompleteModal,
        handleWelcomeStart,
        handleWelcomeSkip,
        handleCompleteClose
      }}
    >
      <TutorialWelcomeModal
        isOpen={showWelcomeModal}
        onSkip={handleWelcomeSkip}
        onStart={handleWelcomeStart}
      />
      <TutorialCompleteModal
        isOpen={showCompleteModal}
        onClose={handleCompleteClose}
      />
      {children}
    </TutorialContext.Provider>
  );
};
