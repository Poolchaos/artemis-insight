"""
PDF processing service for text extraction and semantic chunking.

Extracts text from PDF files with metadata preservation and creates semantic
chunks suitable for embedding generation and semantic search.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pdfplumber
from io import BytesIO


class DocumentChunk:
    """Represents a chunk of text from a document with metadata."""

    def __init__(
        self,
        text: str,
        chunk_index: int,
        page_number: int,
        start_char: int,
        end_char: int,
        section_heading: Optional[str] = None,
        word_count: int = 0
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.start_char = start_char
        self.end_char = end_char
        self.section_heading = section_heading
        self.word_count = word_count or len(text.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "text": self.text,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "section_heading": self.section_heading,
            "word_count": self.word_count
        }


class PDFProcessor:
    """Service for processing PDF documents."""

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        min_chunk_size: int = 100
    ):
        """
        Initialize PDF processor.

        Args:
            chunk_size: Target number of words per chunk
            overlap: Number of words to overlap between chunks
            min_chunk_size: Minimum chunk size in words
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def extract_text_from_pdf(
        self,
        file_path: str = None,
        file_bytes: bytes = None
    ) -> Dict[str, Any]:
        """
        Extract text from PDF with page-level metadata.

        Args:
            file_path: Path to PDF file
            file_bytes: Raw PDF bytes

        Returns:
            Dictionary with full_text, pages, and metadata

        Raises:
            ValueError: If neither file_path nor file_bytes provided
        """
        if not file_path and not file_bytes:
            raise ValueError("Either file_path or file_bytes must be provided")

        pages_data = []
        full_text = []

        # Open PDF from path or bytes
        if file_bytes:
            pdf_file = BytesIO(file_bytes)
            pdf = pdfplumber.open(pdf_file)
        else:
            pdf = pdfplumber.open(file_path)

        try:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()

                if text:
                    # Clean up text
                    text = self._clean_text(text)

                    pages_data.append({
                        "page_number": page_num,
                        "text": text,
                        "char_count": len(text),
                        "word_count": len(text.split())
                    })

                    full_text.append(text)

            complete_text = "\n\n".join(full_text)

            return {
                "full_text": complete_text,
                "pages": pages_data,
                "total_pages": len(pages_data),
                "total_words": len(complete_text.split()),
                "total_chars": len(complete_text)
            }

        finally:
            pdf.close()

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing artifacts and normalizing whitespace.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove page numbers (common patterns)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def detect_headings(self, text: str) -> List[Tuple[str, int]]:
        """
        Detect section headings in text.

        Args:
            text: Document text

        Returns:
            List of (heading, position) tuples
        """
        headings = []

        # Common heading patterns
        patterns = [
            # Numbered headings: "1. Introduction", "1.1 Background"
            r'^(\d+\.?\d*\.?\s+[A-Z][^\n]{5,60})$',
            # All caps headings: "INTRODUCTION"
            r'^([A-Z][A-Z\s]{5,60})$',
            # Title case at start of line: "Introduction and Background"
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,8})$'
        ]

        lines = text.split('\n')
        char_pos = 0

        for line in lines:
            line_stripped = line.strip()

            for pattern in patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    heading = match.group(1).strip()
                    # Filter out very short or very long matches
                    if 5 <= len(heading) <= 100:
                        headings.append((heading, char_pos))
                    break

            char_pos += len(line) + 1  # +1 for newline

        return headings

    def create_semantic_chunks(
        self,
        extracted_data: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Create semantic chunks from extracted PDF data.

        Uses a sliding window approach with overlap to ensure context preservation.
        Attempts to split at sentence boundaries when possible.

        Args:
            extracted_data: Output from extract_text_from_pdf

        Returns:
            List of DocumentChunk objects
        """
        full_text = extracted_data["full_text"]
        pages_data = extracted_data["pages"]
        total_pages = extracted_data["total_pages"]

        # Detect headings for context
        headings = self.detect_headings(full_text)

        # Split into words for accurate tracking
        all_words = full_text.split()
        total_words = len(all_words)

        # Build page position map (character-based)
        page_positions = self._build_page_positions(pages_data)

        chunks = []
        chunk_index = 0
        word_index = 0

        while word_index < total_words:
            # Collect words for this chunk
            chunk_end = min(word_index + self.chunk_size, total_words)
            chunk_words = all_words[word_index:chunk_end]

            # Skip if too small
            if len(chunk_words) < self.min_chunk_size and word_index > 0:
                break

            # Create chunk text
            chunk_text = ' '.join(chunk_words)

            # Estimate character position (approximate but consistent)
            # Average English word is ~5 chars + 1 space = 6 chars
            approx_char_position = word_index * 6

            # Determine page number and heading
            current_page = self._get_page_at_position(approx_char_position, page_positions)
            # Clamp to valid page range
            current_page = max(1, min(current_page, total_pages))

            current_heading = self._get_heading_at_position(approx_char_position, headings)

            # Create chunk
            chunk = DocumentChunk(
                text=chunk_text,
                chunk_index=chunk_index,
                page_number=current_page,
                start_char=approx_char_position,
                end_char=approx_char_position + len(chunk_text),
                section_heading=current_heading,
                word_count=len(chunk_words)
            )
            chunks.append(chunk)
            chunk_index += 1

            # Move to next chunk with overlap
            if self.overlap > 0 and word_index + self.chunk_size < total_words:
                word_index += self.chunk_size - self.overlap
            else:
                word_index += self.chunk_size

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be enhanced)
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text)

        # Filter out empty sentences
        return [s.strip() for s in sentences if s.strip()]

    def _build_page_positions(
        self,
        pages_data: List[Dict[str, Any]]
    ) -> List[Tuple[int, int, int]]:
        """
        Build a map of character positions to page numbers.

        Args:
            pages_data: Page data from extract_text_from_pdf

        Returns:
            List of (page_number, start_char, end_char) tuples
        """
        positions = []
        char_pos = 0

        for page in pages_data:
            page_text = page["text"]
            page_len = len(page_text) + 2  # +2 for \n\n separator

            positions.append((
                page["page_number"],
                char_pos,
                char_pos + page_len
            ))

            char_pos += page_len

        return positions

    def _get_page_at_position(
        self,
        position: int,
        page_positions: List[Tuple[int, int, int]]
    ) -> int:
        """
        Get page number at character position.

        Args:
            position: Character position in full text
            page_positions: Output from _build_page_positions

        Returns:
            Page number (1-indexed)
        """
        for page_num, start, end in page_positions:
            if start <= position < end:
                return page_num

        # Default to last page if position is beyond
        return page_positions[-1][0] if page_positions else 1

    def _get_heading_at_position(
        self,
        position: int,
        headings: List[Tuple[str, int]]
    ) -> Optional[str]:
        """
        Get the most recent heading before a position.

        Args:
            position: Character position in text
            headings: List of (heading, position) tuples

        Returns:
            Heading text or None
        """
        current_heading = None

        for heading, heading_pos in headings:
            if heading_pos <= position:
                current_heading = heading
            else:
                break

        return current_heading

    def process_pdf(
        self,
        file_path: str = None,
        file_bytes: bytes = None
    ) -> Dict[str, Any]:
        """
        Complete PDF processing pipeline.

        Extracts text, creates chunks, and returns all data.

        Args:
            file_path: Path to PDF file
            file_bytes: Raw PDF bytes

        Returns:
            Dictionary with extracted_data and chunks
        """
        # Extract text
        extracted_data = self.extract_text_from_pdf(
            file_path=file_path,
            file_bytes=file_bytes
        )

        # Create chunks
        chunks = self.create_semantic_chunks(extracted_data)

        return {
            "extracted_data": extracted_data,
            "chunks": [chunk.to_dict() for chunk in chunks],
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(c.word_count for c in chunks) / len(chunks) if chunks else 0
        }
