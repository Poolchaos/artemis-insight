import { useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTutorial } from '../contexts/TutorialContext';

export const TutorialAutoStart = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { startTutorial } = useTutorial();
  const hasTriggered = useRef(false);

  // Only trigger once on dashboard for first-time users
  if (!hasTriggered.current && location.pathname === '/dashboard') {
    const TUTORIAL_COMPLETED_KEY = 'artemis-tutorial-completed';
    const hasCompletedTutorial = localStorage.getItem(TUTORIAL_COMPLETED_KEY);

    if (!hasCompletedTutorial) {
      hasTriggered.current = true;
      // Delay to ensure DOM is ready
      setTimeout(() => {
        startTutorial(navigate);
      }, 1000);
    }
  }

  return null;
};
