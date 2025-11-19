"""
Embedding service for generating and managing vector embeddings.

Generates embeddings using OpenAI text-embedding-3-small (1536 dimensions)
for semantic search and multi-pass AI processing.
"""

import asyncio
import math
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.config import settings
from app.models.embedding import (
    EmbeddingCreate,
    EmbeddingInDB,
    EmbeddingSearchQuery,
    EmbeddingSearchResult,
    SimilarChunk
)
from app.services.pdf_processor import DocumentChunk


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score between 0 and 1
    """
    # Dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    # Cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)

    # Clamp to [0, 1] range (should already be in [-1, 1])
    return max(0.0, min(1.0, similarity))


class EmbeddingService:
    """Service for generating and managing embeddings."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize embedding service.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.embeddings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model  # text-embedding-3-small
        self.batch_size = 100  # OpenAI allows up to 2048 inputs per request

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text to embed

        Returns:
            1536-dimensional embedding vector

        Raises:
            Exception: If OpenAI API call fails
        """
        response = await self.client.embeddings.create(
            input=text,
            model=self.model
        )

        return response.data[0].embedding

    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of text strings to embed (max 100 per batch)

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If too many texts provided
            Exception: If OpenAI API call fails
        """
        if len(texts) > self.batch_size:
            raise ValueError(f"Batch size {len(texts)} exceeds maximum {self.batch_size}")

        response = await self.client.embeddings.create(
            input=texts,
            model=self.model
        )

        # Ensure embeddings are returned in the same order as input
        return [item.embedding for item in response.data]

    async def generate_embeddings_for_chunks(
        self,
        chunks: List[DocumentChunk],
        document_id: str,
        batch_size: Optional[int] = None
    ) -> List[str]:
        """
        Generate embeddings for document chunks and store in database.

        Processes chunks in batches for efficiency. Progress can be tracked
        by monitoring database insertion.

        Args:
            chunks: List of DocumentChunk objects from PDFProcessor
            document_id: MongoDB document ID
            batch_size: Optional batch size (default: 100)

        Returns:
            List of embedding IDs created

        Raises:
            ValueError: If chunks list is empty
        """
        if not chunks:
            raise ValueError("Cannot generate embeddings for empty chunks list")

        batch_size = batch_size or self.batch_size
        embedding_ids = []
        total_chunks = len(chunks)
        total_batches = (total_chunks + batch_size - 1) // batch_size

        logger.info(f"Generating embeddings for {total_chunks} chunks in {total_batches} batches")

        # Process chunks in batches
        for batch_num, i in enumerate(range(0, len(chunks), batch_size), 1):
            batch = chunks[i:i + batch_size]
            batch_texts = [chunk.text for chunk in batch]

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            # Generate embeddings for batch
            embeddings = await self.generate_embeddings_batch(batch_texts)

            # Create embedding documents
            embedding_docs = []
            for chunk, embedding in zip(batch, embeddings):
                embedding_doc = {
                    "document_id": ObjectId(document_id),
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.text,
                    "embedding_vector": embedding,
                    "page_number": chunk.page_number,
                    "section_heading": chunk.section_heading,
                    "word_count": chunk.word_count,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "model": self.model
                }
                embedding_docs.append(embedding_doc)

            # Batch insert to database
            result = await self.collection.insert_many(embedding_docs)
            embedding_ids.extend([str(oid) for oid in result.inserted_ids])

            logger.info(f"Batch {batch_num}/{total_batches} completed: {len(result.inserted_ids)} embeddings saved")

        logger.info(f"All embeddings generated: {len(embedding_ids)} total")
        return embedding_ids

    async def search_similar_chunks(
        self,
        query: EmbeddingSearchQuery
    ) -> List[EmbeddingSearchResult]:
        """
        Search for chunks similar to a query using vector similarity.

        Uses MongoDB's vector search capabilities (requires Atlas or
        vector search index).

        Args:
            query: Search query with vector or text

        Returns:
            List of similar chunks with similarity scores

        Note:
            This is a simplified implementation. For production, use MongoDB
            Atlas Vector Search or implement cosine similarity in-memory.
        """
        # Get query vector
        if query.query_vector:
            query_vector = query.query_vector
        else:
            # Generate embedding from query text
            query_vector = await self.generate_embedding(query.query_text)

        # Build MongoDB query
        mongo_query: Dict[str, Any] = {}
        if query.document_id:
            mongo_query["document_id"] = ObjectId(query.document_id)

        # Fetch embeddings (in production, use vector search index)
        # For now, fetch all matching embeddings and compute similarity in Python
        cursor = self.collection.find(mongo_query)
        embeddings = await cursor.to_list(length=None)

        # Compute cosine similarity for each embedding
        results = []
        for emb in embeddings:
            similarity = cosine_similarity(query_vector, emb["embedding_vector"])

            if similarity >= query.min_similarity:
                results.append({
                    "embedding_id": str(emb["_id"]),
                    "document_id": str(emb["document_id"]),
                    "chunk_index": emb["chunk_index"],
                    "chunk_text": emb["chunk_text"],
                    "page_number": emb["page_number"],
                    "section_heading": emb.get("section_heading"),
                    "word_count": emb["word_count"],
                    "similarity_score": similarity
                })

        # Sort by similarity score descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Return top_k results
        return [EmbeddingSearchResult(**r) for r in results[:query.top_k]]

    async def get_embeddings_for_document(
        self,
        document_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all embeddings for a specific document.

        Args:
            document_id: Document ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of embedding documents
        """
        cursor = self.collection.find(
            {"document_id": ObjectId(document_id)}
        ).sort("chunk_index", 1).skip(skip).limit(limit)

        embeddings = await cursor.to_list(length=limit)

        # Convert ObjectIds to strings
        for emb in embeddings:
            emb["_id"] = str(emb["_id"])
            emb["document_id"] = str(emb["document_id"])

        return embeddings

    async def delete_embeddings_for_document(self, document_id: str) -> int:
        """
        Delete all embeddings for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of embeddings deleted
        """
        result = await self.collection.delete_many(
            {"document_id": ObjectId(document_id)}
        )

        return result.deleted_count

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score between 0 and 1
        """
        import math

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)

        # Clamp to [0, 1] range (should already be in [-1, 1])
        return max(0.0, min(1.0, similarity))

    async def count_embeddings(self, document_id: Optional[str] = None) -> int:
        """
        Count embeddings, optionally filtered by document.

        Args:
            document_id: Optional document ID filter

        Returns:
            Number of embeddings
        """
        query = {}
        if document_id:
            query["document_id"] = ObjectId(document_id)

        return await self.collection.count_documents(query)

