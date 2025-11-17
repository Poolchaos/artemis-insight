import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';
import { authService } from '../services/auth.service';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  fetchCurrentUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      setUser: (user) => set({ user, isAuthenticated: !!user }),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authService.login({ email, password });
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false
          });
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Login failed';
          set({ error: message, isLoading: false });
          throw error;
        }
      },

      register: async (email, name, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authService.register({ email, name, password });
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false
          });
        } catch (error: any) {
          // Map technical errors to user-friendly messages
          let message = 'Unable to create account. Please try again.';

          if (error.response?.status === 404) {
            message = 'Registration service is temporarily unavailable. Please try again later.';
          } else if (error.response?.status === 400) {
            const detail = error.response?.data?.detail || '';
            if (detail.toLowerCase().includes('email') && detail.toLowerCase().includes('exist')) {
              message = 'An account with this email already exists. Please sign in or use a different email.';
            } else if (detail.toLowerCase().includes('password')) {
              message = 'Password does not meet requirements. Please use a stronger password.';
            } else {
              message = detail || 'Invalid information provided. Please check your details.';
            }
          } else if (error.response?.status === 500) {
            message = 'Server error occurred. Please try again later.';
          } else if (error.message === 'Network Error') {
            message = 'Unable to connect to the server. Please check your internet connection.';
          }

          set({ error: message, isLoading: false });
          throw error;
        }
      },

      logout: () => {
        authService.logout();
        set({ user: null, isAuthenticated: false, error: null });
      },

      fetchCurrentUser: async () => {
        if (!authService.isAuthenticated()) {
          set({ user: null, isAuthenticated: false });
          return;
        }

        set({ isLoading: true });
        try {
          const user = await authService.getCurrentUser();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          authService.logout();
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      }),
    }
  )
);
