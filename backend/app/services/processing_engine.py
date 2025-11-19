"""
Multi-pass AI processing engine for document summarization.

Implements a 4-pass approach:
- Pass 1: Document indexing (PDF → chunks → embeddings)
- Pass 2: Thematic querying (template guidance prompts → semantic search)
- Pass 3: Section synthesis (relevant chunks → OpenAI → section summaries)
- Pass 4: Final assembly (sections → formatted document)
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone
from openai import AsyncOpenAI, APITimeoutError, RateLimitError, APIError
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.config import settings
from app.services.pdf_processor import PDFProcessor
from app.services.embedding_service import EmbeddingService
from app.models.template import TemplateInDB, TemplateSection
from app.models.embedding import EmbeddingSearchQuery

logger = logging.getLogger(__name__)


class ProcessingEngine:
    """Multi-pass document processing engine."""

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # seconds
    OPENAI_TIMEOUT = 120  # seconds per API call

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize processing engine.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.pdf_processor = PDFProcessor()
        self.embedding_service = EmbeddingService(db)
        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=self.OPENAI_TIMEOUT
        )

    async def process_document(
        self,
        document_id: str,
        file_path: str,
        template: TemplateInDB,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a document through all 4 passes.

        Args:
            document_id: MongoDB document ID
            file_path: Path to PDF file
            template: Template to use for summarization
            progress_callback: Optional callback for progress updates (sync function)

        Returns:
            Dictionary with processed sections and metadata
        """
        result = {
            "document_id": document_id,
            "template_id": str(template.id),
            "template_name": template.name,
            "started_at": datetime.now(timezone.utc),
            "sections": [],
            "metadata": {}
        }

        try:
            # Pass 1: Document Indexing
            if progress_callback:
                progress_callback("pass_1", "Extracting text and creating chunks")

            logger.info(f"Starting Pass 1: Document indexing for {document_id}")
            indexing_result = await self._pass_1_index_document(
                document_id, file_path, template
            )

            result["metadata"]["total_pages"] = indexing_result["total_pages"]
            result["metadata"]["total_words"] = indexing_result["total_words"]
            result["metadata"]["total_chunks"] = indexing_result["total_chunks"]
            result["metadata"]["embedding_count"] = indexing_result["embedding_count"]

            logger.info(f"Pass 1 completed: {indexing_result['total_chunks']} chunks, {indexing_result['embedding_count']} embeddings")

            # Pass 2, 3, 4: Process each section with progress tracking
            total_sections = len(template.sections)
            for idx, section in enumerate(template.sections, 1):
                if progress_callback:
                    progress_callback(
                        "section_processing",
                        f"Processing section {idx}/{total_sections}: {section.title}"
                    )

                logger.info(f"Processing section {idx}/{total_sections}: {section.title}")

                section_result = await self._process_section(
                    document_id,
                    section,
                    template,
                    indexing_result
                )

                result["sections"].append(section_result)
                logger.info(f"Section '{section.title}' completed: {section_result['word_count']} words")

            result["completed_at"] = datetime.now(timezone.utc)
            result["status"] = "completed"

            logger.info(f"Document processing completed: {len(result['sections'])} sections generated")

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}", exc_info=True)
            result["status"] = "failed"
            result["error"] = str(e)
            result["failed_at"] = datetime.now(timezone.utc)
            raise

        return result

    async def _pass_1_index_document(
        self,
        document_id: str,
        file_path: str,
        template: TemplateInDB
    ) -> Dict[str, Any]:
        """
        Pass 1: Extract text, create chunks, and generate embeddings.

        Args:
            document_id: Document ID
            file_path: Path to PDF
            template: Template with processing strategy

        Returns:
            Indexing results with metadata
        """
        # Extract text and create chunks using template's chunk settings
        strategy = template.processing_strategy
        processor = PDFProcessor(
            chunk_size=strategy.chunk_size,
            overlap=strategy.overlap,
            min_chunk_size=100
        )

        processing_result = processor.process_pdf(file_path=file_path)
        extracted_data = processing_result["extracted_data"]
        chunks = processing_result["chunks"]

        # Convert chunk dicts back to DocumentChunk objects for embedding service
        from app.services.pdf_processor import DocumentChunk
        chunk_objects = [
            DocumentChunk(
                text=c["text"],
                chunk_index=c["chunk_index"],
                page_number=c["page_number"],
                start_char=c["start_char"],
                end_char=c["end_char"],
                section_heading=c.get("section_heading"),
                word_count=c["word_count"]
            )
            for c in chunks
        ]

        # Generate embeddings
        embedding_ids = await self.embedding_service.generate_embeddings_for_chunks(
            chunk_objects,
            document_id
        )

        return {
            "total_pages": extracted_data["total_pages"],
            "total_words": extracted_data["total_words"],
            "total_chunks": len(chunks),
            "embedding_count": len(embedding_ids),
            "chunks": chunks,
            "extracted_data": extracted_data
        }

    async def _process_section(
        self,
        document_id: str,
        section: TemplateSection,
        template: TemplateInDB,
        indexing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single template section through Passes 2-4.

        Args:
            document_id: Document ID
            section: Template section to process
            template: Full template
            indexing_result: Results from Pass 1

        Returns:
            Section processing results
        """
        # Pass 2: Thematic Querying
        relevant_chunks = await self._pass_2_query_relevant_chunks(
            document_id,
            section,
            template
        )

        # Pass 3: Section Synthesis
        section_summary = await self._pass_3_synthesize_section(
            section,
            relevant_chunks,
            template
        )

        # Pass 4: Final Assembly (metadata and formatting)
        return {
            "title": section.title,
            "order": section.order,
            "content": section_summary,
            "source_chunks": len(relevant_chunks),
            "pages_referenced": list(set(c["page_number"] for c in relevant_chunks)),
            "word_count": len(section_summary.split()),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _pass_2_query_relevant_chunks(
        self,
        document_id: str,
        section: TemplateSection,
        template: TemplateInDB
    ) -> List[Dict[str, Any]]:
        """
        Pass 2: Use section guidance prompt to find relevant chunks via semantic search.

        Args:
            document_id: Document ID
            section: Template section
            template: Full template

        Returns:
            List of relevant chunk data
        """
        # Use the guidance prompt as the search query
        query = EmbeddingSearchQuery(
            query_text=section.guidance_prompt,
            document_id=document_id,
            top_k=20,  # Get top 20 most relevant chunks
            min_similarity=0.3  # Lower threshold for broader coverage
        )

        search_results = await self.embedding_service.search_similar_chunks(query)

        # Convert to dict format with similarity scores
        return [
            {
                "chunk_text": result.chunk_text,
                "chunk_index": result.chunk_index,
                "page_number": result.page_number,
                "section_heading": result.section_heading,
                "word_count": result.word_count,
                "similarity_score": result.similarity_score
            }
            for result in search_results
        ]

    async def _pass_3_synthesize_section(
        self,
        section: TemplateSection,
        relevant_chunks: List[Dict[str, Any]],
        template: TemplateInDB
    ) -> str:
        """
        Pass 3: Use OpenAI to synthesize section content from relevant chunks.
        Includes retry logic with exponential backoff for transient failures.

        Args:
            section: Template section
            relevant_chunks: Relevant chunks from Pass 2
            template: Full template

        Returns:
            Synthesized section content
        """
        if not relevant_chunks:
            logger.warning(f"No relevant chunks found for section: {section.title}")
            return f"No relevant content found for section: {section.title}"

        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(relevant_chunks[:15], 1):  # Use top 15 chunks
            context_parts.append(
                f"[Chunk {i} - Page {chunk['page_number']}, "
                f"Similarity: {chunk['similarity_score']:.2f}]\n"
                f"{chunk['chunk_text']}\n"
            )

        context = "\n---\n".join(context_parts)

        # Create synthesis prompt
        synthesis_prompt = f"""You are tasked with synthesizing a section for a document summary.

**Section Title:** {section.title}

**Guidance:** {section.guidance_prompt}

**Source Material:**
{context}

**Instructions:**
- Create a comprehensive summary for the "{section.title}" section
- Follow the guidance instructions carefully
- Use information from the provided chunks
- Include specific details, figures, and references when available
- Reference page numbers when citing specific information
- Maintain a professional, technical tone
- Keep the summary focused and relevant to the section title
- If the chunks contain tables or figures, describe them or reference them by their numbers

Write the section content now:"""

        # Call OpenAI with retry logic
        strategy = template.processing_strategy

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"OpenAI API call attempt {attempt}/{self.MAX_RETRIES} for section: {section.title}")

                response = await self.openai_client.chat.completions.create(
                    model=strategy.summarization_model,
                    messages=[
                        {"role": "system", "content": template.system_prompt},
                        {"role": "user", "content": synthesis_prompt}
                    ],
                    max_tokens=strategy.max_tokens_per_section,
                    temperature=strategy.temperature
                )

                content = response.choices[0].message.content.strip()
                logger.info(f"OpenAI API call successful for section: {section.title} ({len(content)} chars)")
                return content

            except APITimeoutError as e:
                logger.warning(f"OpenAI API timeout (attempt {attempt}/{self.MAX_RETRIES}): {str(e)}")
                if attempt == self.MAX_RETRIES:
                    raise Exception(f"OpenAI API timeout after {self.MAX_RETRIES} attempts. Please try again later.") from e
                await asyncio.sleep(self.RETRY_DELAY_BASE ** attempt)

            except RateLimitError as e:
                logger.warning(f"OpenAI rate limit hit (attempt {attempt}/{self.MAX_RETRIES}): {str(e)}")
                if attempt == self.MAX_RETRIES:
                    raise Exception(f"OpenAI rate limit exceeded. Please wait a few minutes and try again.") from e
                # Exponential backoff for rate limits
                await asyncio.sleep(self.RETRY_DELAY_BASE ** (attempt + 1))

            except APIError as e:
                logger.error(f"OpenAI API error (attempt {attempt}/{self.MAX_RETRIES}): {str(e)}")
                if attempt == self.MAX_RETRIES:
                    raise Exception(f"OpenAI API error: {str(e)}") from e
                await asyncio.sleep(self.RETRY_DELAY_BASE ** attempt)

            except Exception as e:
                logger.error(f"Unexpected error calling OpenAI (attempt {attempt}/{self.MAX_RETRIES}): {str(e)}", exc_info=True)
                if attempt == self.MAX_RETRIES:
                    raise
                await asyncio.sleep(self.RETRY_DELAY_BASE ** attempt)

        # Should never reach here, but for safety
        raise Exception("Failed to synthesize section after maximum retries")

    async def regenerate_section(
        self,
        document_id: str,
        section_title: str,
        template: TemplateInDB,
        indexing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Regenerate a single section (useful for iterative refinement).

        Args:
            document_id: Document ID
            section_title: Title of section to regenerate
            template: Template
            indexing_result: Cached indexing results

        Returns:
            Regenerated section data
        """
        # Find the section
        section = next(
            (s for s in template.sections if s.title == section_title),
            None
        )

        if not section:
            raise ValueError(f"Section '{section_title}' not found in template")

        return await self._process_section(
            document_id,
            section,
            template,
            indexing_result
        )

    async def estimate_processing_cost(
        self,
        file_path: str,
        template: TemplateInDB
    ) -> Dict[str, Any]:
        """
        Estimate processing cost before running.

        Args:
            file_path: Path to PDF
            template: Template to use

        Returns:
            Cost estimates
        """
        # Quick extraction to get word count
        processor = PDFProcessor()
        extracted = processor.extract_text_from_pdf(file_path=file_path)

        total_words = extracted["total_words"]
        chunk_size = template.processing_strategy.chunk_size

        # Estimate chunks
        estimated_chunks = total_words // chunk_size

        # OpenAI pricing (approximate, adjust as needed)
        embedding_cost_per_1k = 0.00002  # $0.02 per 1M tokens for text-embedding-3-small
        gpt4_cost_per_1k_input = 0.0025  # $2.50 per 1M tokens for gpt-4o-mini input
        gpt4_cost_per_1k_output = 0.01  # $10 per 1M tokens for gpt-4o-mini output

        # Embedding cost
        embedding_tokens = total_words * 1.3  # Rough token estimate
        embedding_cost = (embedding_tokens / 1000) * embedding_cost_per_1k

        # Synthesis cost (per section)
        section_count = len(template.sections)
        avg_context_words = 15 * chunk_size  # Top 15 chunks per section
        synthesis_input_tokens = (avg_context_words * 1.3 * section_count) / 1000
        synthesis_output_tokens = (template.processing_strategy.max_tokens_per_section * section_count) / 1000

        synthesis_cost = (
            synthesis_input_tokens * gpt4_cost_per_1k_input +
            synthesis_output_tokens * gpt4_cost_per_1k_output
        )

        total_cost = embedding_cost + synthesis_cost

        return {
            "total_words": total_words,
            "estimated_chunks": estimated_chunks,
            "section_count": section_count,
            "costs": {
                "embedding": round(embedding_cost, 4),
                "synthesis": round(synthesis_cost, 4),
                "total": round(total_cost, 4),
                "currency": "USD"
            },
            "estimated_duration_minutes": (estimated_chunks // 100) * 2 + section_count * 0.5
        }
