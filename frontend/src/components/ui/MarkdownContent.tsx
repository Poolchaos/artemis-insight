interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * Simple markdown renderer for summary content
 * Handles common markdown elements like headers, bold, italic, lists
 */
export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  // Simple markdown to HTML conversion
  const renderMarkdown = (text: string): string => {
    return text
      // Headers
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-5 mb-3">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-6 mb-4">$1</h1>')
      // Bold
      .replace(/\*\*(.*?)\*\*/gim, '<strong class="font-semibold text-gray-900 dark:text-gray-100">$1</strong>')
      // Italic
      .replace(/\*(.*?)\*/gim, '<em class="italic">$1</em>')
      // Unordered lists
      .replace(/^- (.*$)/gim, '<li class="ml-4">• $1</li>')
      .replace(/^\* (.*$)/gim, '<li class="ml-4">• $1</li>')
      // Numbered lists
      .replace(/^(\d+)\. (.*$)/gim, '<li class="ml-4">$1. $2</li>')
      // Line breaks
      .replace(/\n\n/g, '</p><p class="mb-3">')
      .replace(/\n/g, '<br/>');
  };

  const htmlContent = `<p class="mb-3">${renderMarkdown(content)}</p>`;

  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-none ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}
