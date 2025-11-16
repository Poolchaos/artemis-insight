"""
Integration tests for PDF processing with real feasibility study document.

Tests using: example-file-upload/O992-ILF-OD-0012_Water Resources_RevFinal.pdf (365+ pages)
"""

import pytest
from pathlib import Path
from app.services.pdf_processor import PDFProcessor


@pytest.mark.asyncio
class TestRealPDFProcessing:
    """Integration tests with real feasibility study PDF."""

    @pytest.fixture
    def real_pdf_path(self):
        """Path to the real feasibility study PDF."""
        # Path from backend directory: /app/example-file-upload/...
        pdf_path = Path("/app/example-file-upload/O992-ILF-OD-0012_Water Resources_RevFinal.pdf")

        if not pdf_path.exists():
            pytest.skip(f"Real PDF not found at {pdf_path}")

        return str(pdf_path)

    @pytest.fixture
    def processor(self):
        """Create processor with production settings."""
        return PDFProcessor(chunk_size=500, overlap=50, min_chunk_size=100)

    def test_extract_text_from_real_pdf(self, processor, real_pdf_path):
        """Test text extraction from real 365+ page document."""
        extracted_data = processor.extract_text_from_pdf(file_path=real_pdf_path)

        # Should have many pages
        assert extracted_data["total_pages"] > 200, f"Expected 200+ pages, got {extracted_data['total_pages']}"
        assert len(extracted_data["pages"]) == extracted_data["total_pages"]

        # Should have substantial content
        assert extracted_data["total_words"] > 10000, f"Expected 10k+ words, got {extracted_data['total_words']}"
        assert extracted_data["total_chars"] > 50000

        # Should have full text
        assert len(extracted_data["full_text"]) > 0

        print(f"\n✓ Extracted {extracted_data['total_pages']} pages")
        print(f"✓ Total words: {extracted_data['total_words']:,}")
        print(f"✓ Total characters: {extracted_data['total_chars']:,}")

    def test_detect_headings_in_real_pdf(self, processor, real_pdf_path):
        """Test heading detection in real feasibility study."""
        extracted_data = processor.extract_text_from_pdf(file_path=real_pdf_path)
        headings = processor.detect_headings(extracted_data["full_text"])

        # Should detect multiple headings in a feasibility study
        assert len(headings) > 5, f"Expected multiple headings, found {len(headings)}"

        # Print sample headings
        print(f"\n✓ Detected {len(headings)} headings")
        print("\nSample headings:")
        for heading, pos in headings[:10]:
            print(f"  - {heading[:80]}")

    def test_create_chunks_from_real_pdf(self, processor, real_pdf_path):
        """Test semantic chunking of real document."""
        extracted_data = processor.extract_text_from_pdf(file_path=real_pdf_path)
        chunks = processor.create_semantic_chunks(extracted_data)

        print(f"\n✓ Created {len(chunks)} chunks from {extracted_data['total_pages']} pages")

        # Should create many chunks for 365+ pages
        expected_min_chunks = 50  # Conservative estimate
        assert len(chunks) >= expected_min_chunks, \
            f"Expected at least {expected_min_chunks} chunks, got {len(chunks)}"

        # Verify chunk properties
        assert all(chunk.word_count > 0 for chunk in chunks), "Some chunks have zero words"

        # Check page numbers
        invalid_pages = [c for c in chunks if c.page_number < 1 or c.page_number > extracted_data["total_pages"]]
        if invalid_pages:
            print(f"\nInvalid page numbers found in {len(invalid_pages)} chunks:")
            for c in invalid_pages[:5]:
                print(f"  Chunk {c.chunk_index}: page {c.page_number} (should be 1-{extracted_data['total_pages']})")

        assert all(chunk.page_number >= 1 for chunk in chunks), "Some chunks have page_number < 1"
        assert all(chunk.page_number <= extracted_data["total_pages"] for chunk in chunks), \
            f"Some chunks have page_number > {extracted_data['total_pages']}"

        # Check chunk sizes are reasonable
        avg_chunk_size = sum(c.word_count for c in chunks) / len(chunks)
        assert 300 <= avg_chunk_size <= 700, \
            f"Average chunk size {avg_chunk_size} outside expected range (300-700 words)"

        print(f"✓ Average chunk size: {avg_chunk_size:.0f} words")
        print(f"✓ Chunk size range: {min(c.word_count for c in chunks)}-{max(c.word_count for c in chunks)} words")

    def test_full_processing_pipeline(self, processor, real_pdf_path):
        """Test complete processing pipeline with real PDF."""
        result = processor.process_pdf(file_path=real_pdf_path)

        # Verify all components
        assert "extracted_data" in result
        assert "chunks" in result
        assert "total_chunks" in result
        assert "avg_chunk_size" in result

        # Check extracted data
        extracted = result["extracted_data"]
        assert extracted["total_pages"] > 200

        # Check chunks
        chunks = result["chunks"]
        assert len(chunks) == result["total_chunks"]
        assert result["total_chunks"] > 50

        # Verify chunks have all required fields
        required_fields = ["text", "chunk_index", "page_number", "start_char",
                          "end_char", "word_count"]
        for chunk in chunks:
            for field in required_fields:
                assert field in chunk, f"Chunk missing required field: {field}"

        # Verify chunk indices are sequential
        indices = [chunk["chunk_index"] for chunk in chunks]
        assert indices == list(range(len(chunks))), "Chunk indices not sequential"

        print(f"\n✓ Full pipeline successful")
        print(f"✓ Processed {extracted['total_pages']} pages into {result['total_chunks']} chunks")
        print(f"✓ Average chunk size: {result['avg_chunk_size']:.1f} words")

    def test_chunk_coverage(self, processor, real_pdf_path):
        """Test that chunks cover the entire document."""
        extracted_data = processor.extract_text_from_pdf(file_path=real_pdf_path)
        chunks = processor.create_semantic_chunks(extracted_data)

        # Calculate coverage
        total_words = extracted_data["total_words"]
        chunk_words = sum(c.word_count for c in chunks)

        # With overlap, chunk words will be more than total words
        # But should be within reasonable bounds (1-2x due to overlap)
        assert chunk_words >= total_words * 0.8, \
            f"Chunks cover too few words: {chunk_words} vs {total_words}"
        assert chunk_words <= total_words * 2.0, \
            f"Chunks have excessive overlap: {chunk_words} vs {total_words}"

        coverage_ratio = chunk_words / total_words
        print(f"\n✓ Coverage ratio: {coverage_ratio:.2f}x (includes overlap)")

    def test_page_distribution(self, processor, real_pdf_path):
        """Test that chunks are distributed across all pages."""
        extracted_data = processor.extract_text_from_pdf(file_path=real_pdf_path)
        chunks = processor.create_semantic_chunks(extracted_data)

        # Get unique pages referenced in chunks
        pages_in_chunks = set(c.page_number for c in chunks)
        total_pages = extracted_data["total_pages"]

        # Should cover most pages (allowing for some pages with minimal text)
        coverage = len(pages_in_chunks) / total_pages
        assert coverage >= 0.7, \
            f"Chunks only cover {coverage:.1%} of pages ({len(pages_in_chunks)}/{total_pages})"

        print(f"\n✓ Chunks span {len(pages_in_chunks)} of {total_pages} pages ({coverage:.1%} coverage)")

    def test_section_heading_preservation(self, processor, real_pdf_path):
        """Test that section headings are preserved in chunks."""
        extracted_data = processor.extract_text_from_pdf(file_path=real_pdf_path)
        chunks = processor.create_semantic_chunks(extracted_data)

        # Count chunks with section headings
        chunks_with_headings = [c for c in chunks if c.section_heading is not None]

        # Some chunks should have headings (even if detection isn't perfect)
        heading_ratio = len(chunks_with_headings) / len(chunks)

        print(f"\n✓ {len(chunks_with_headings)} of {len(chunks)} chunks have section headings ({heading_ratio:.1%})")

        # Show sample headings
        if chunks_with_headings:
            print("\nSample section headings in chunks:")
            unique_headings = list(set(c.section_heading for c in chunks_with_headings[:20]))
            for heading in unique_headings[:5]:
                print(f"  - {heading}")

    @pytest.mark.slow
    def test_processing_performance(self, processor, real_pdf_path):
        """Test processing performance (marked as slow)."""
        import time

        start_time = time.time()
        result = processor.process_pdf(file_path=real_pdf_path)
        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (adjust based on system)
        # For 365 pages, expecting < 60 seconds
        assert elapsed_time < 120, f"Processing took too long: {elapsed_time:.1f}s"

        pages_per_second = result["extracted_data"]["total_pages"] / elapsed_time

        print(f"\n✓ Processing time: {elapsed_time:.1f}s")
        print(f"✓ Processing speed: {pages_per_second:.1f} pages/second")
