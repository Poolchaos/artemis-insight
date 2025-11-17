import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeStore {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      toggleTheme: () => {
        const currentTheme = get().theme;
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        console.log('[ThemeStore] toggleTheme: current =', currentTheme, ', new =', newTheme);

        if (typeof document !== 'undefined') {
          if (newTheme === 'dark') {
            document.documentElement.classList.add('dark');
            console.log('[ThemeStore] Added dark class to documentElement');
          } else {
            document.documentElement.classList.remove('dark');
            console.log('[ThemeStore] Removed dark class from documentElement');
          }
          console.log('[ThemeStore] Current classes:', document.documentElement.className);
        }

        set({ theme: newTheme });
      },
      setTheme: (theme) => {
        console.log('[ThemeStore] setTheme:', theme);
        if (typeof document !== 'undefined') {
          if (theme === 'dark') {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
          console.log('[ThemeStore] Current classes:', document.documentElement.className);
        }
        set({ theme });
      },
    }),
    {
      name: 'theme-storage',
      onRehydrateStorage: () => (state) => {
        // Apply theme after hydration
        console.log('[ThemeStore] onRehydrateStorage, state:', state);
        if (state && typeof document !== 'undefined') {
          if (state.theme === 'dark') {
            document.documentElement.classList.add('dark');
            console.log('[ThemeStore] Rehydrated: Added dark class');
          } else {
            document.documentElement.classList.remove('dark');
            console.log('[ThemeStore] Rehydrated: Removed dark class');
          }
          console.log('[ThemeStore] Current classes:', document.documentElement.className);
        }
      },
    }
  )
);
