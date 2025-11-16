import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <div className="container mx-auto px-4 py-8">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
              Artemis Insight
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              AI-powered document intelligence platform
            </p>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

