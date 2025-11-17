import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
  DocumentTextIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Spinner from '../ui/Spinner';
import Card, { CardContent, CardHeader } from '../ui/Card';
import Badge from '../ui/Badge';
import { useDocumentStore } from '../../stores/document.store';
import { useSearchStore } from '../../stores/search.store';

export function SemanticSearch() {
  const navigate = useNavigate();
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('');
  const [query, setQuery] = useState('');
  const [minSimilarity, setMinSimilarity] = useState(0.7);
  const [topK, setTopK] = useState(10);
  const [showFilters, setShowFilters] = useState(false);

  const { documents, fetchDocuments } = useDocumentStore();
  const { currentSearch, isLoading, error, searchDocument, clearError } = useSearchStore();

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim() || !selectedDocumentId) {
      return;
    }

    clearError();
    await searchDocument({
      document_id: selectedDocumentId,
      query: query.trim(),
      min_similarity: minSimilarity,
      top_k: topK,
    });
  };

  const handleResultClick = (documentId: string) => {
    navigate(`/documents/${documentId}`);
  };

  const highlightMatch = (text: string, query: string) => {
    const queryWords = query.toLowerCase().split(' ').filter(w => w.length > 2);
    let highlighted = text;

    queryWords.forEach(word => {
      const regex = new RegExp(`(${word})`, 'gi');
      highlighted = highlighted.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-700">$1</mark>');
    });

    return highlighted;
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600 dark:text-green-400';
    if (score >= 0.8) return 'text-blue-600 dark:text-blue-400';
    if (score >= 0.7) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const completedDocuments = documents.filter(doc => doc.status === 'completed');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Semantic Search
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Search for specific information within your documents using AI-powered semantic search
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Search Query
            </h2>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
            >
              <AdjustmentsHorizontalIcon className="h-5 w-5" />
              {showFilters ? 'Hide' : 'Show'} Filters
            </button>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="space-y-4">
            {/* Document Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Document
              </label>
              <select
                value={selectedDocumentId}
                onChange={(e) => setSelectedDocumentId(e.target.value)}
                required
                className="
                  w-full px-3 py-2
                  border border-gray-300 dark:border-gray-600 rounded-md
                  bg-white dark:bg-gray-800
                  text-gray-900 dark:text-gray-100
                  focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
              >
                <option value="">Choose a document...</option>
                {completedDocuments.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename}
                  </option>
                ))}
              </select>
              {completedDocuments.length === 0 && (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  No completed documents available. Upload and process a document first.
                </p>
              )}
            </div>

            {/* Query Input */}
            <Input
              label="Search Query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., What are the main findings?"
              helperText="Ask a question or enter keywords to search for"
              required
            />

            {/* Filters */}
            {showFilters && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Minimum Similarity: {minSimilarity.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="1"
                    step="0.05"
                    value={minSimilarity}
                    onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Higher values return more relevant results
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Max Results (Top-K): {topK}
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="50"
                    step="5"
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Maximum number of results to return
                  </p>
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-end">
              <Button
                type="submit"
                isLoading={isLoading}
                disabled={!selectedDocumentId || !query.trim() || isLoading}
              >
                <MagnifyingGlassIcon className="h-5 w-5 mr-2" />
                Search
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Search Results */}
      {currentSearch && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Search Results
              </h2>
              <Badge variant="info">
                {currentSearch.total_results} result{currentSearch.total_results !== 1 ? 's' : ''}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Query: "{currentSearch.query}"
            </p>
          </CardHeader>
          <CardContent>
            {currentSearch.results.length === 0 ? (
              <div className="text-center py-12">
                <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
                <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
                  No results found
                </h3>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Try adjusting your search query or lowering the minimum similarity threshold
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {currentSearch.results.map((result, index) => (
                  <div
                    key={index}
                    className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors cursor-pointer"
                    onClick={() => handleResultClick(selectedDocumentId)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <DocumentTextIcon className="h-5 w-5 text-gray-400" />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              Page {result.page_number}
                            </span>
                            {result.section_heading && (
                              <>
                                <span className="text-gray-400">•</span>
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                  {result.section_heading}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-semibold ${getSimilarityColor(result.score)}`}>
                          {(result.score * 100).toFixed(1)}%
                        </span>
                        <ChevronRightIcon className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>

                    <div
                      className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed"
                      dangerouslySetInnerHTML={{
                        __html: highlightMatch(result.text, currentSearch.query)
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && !currentSearch && (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}
    </div>
  );
}
