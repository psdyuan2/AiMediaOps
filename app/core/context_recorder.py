"""
Context Recorder Module - Persistent storage and retrieval for Context objects.

This module provides long-term memory and history archiving capabilities
using vector databases for efficient storage and semantic search.

Author: Senior Python Backend Architect
"""

import json
import uuid
import asyncio
import logging
import time
import os
import yaml
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass
from enum import Enum

# Import Context from the same module
try:
    from .context import Context
except ImportError:
    # Fallback for standalone usage
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from context import Context


class StorageType(str, Enum):
    """Storage backend types."""
    CHROMA = "chroma"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    FAISS = "faiss"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"


class SearchType(str, Enum):
    """Search types for vector similarity."""
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    KEYWORD = "keyword"
    METADATA = "metadata"


@dataclass
class SearchResult:
    """Container for search results."""
    context_id: str
    similarity_score: float
    metadata: Dict[str, Any]
    context_data: Optional[Context] = None
    created_at: Optional[datetime] = None


@dataclass
class StorageStats:
    """Storage statistics."""
    total_contexts: int
    storage_size_mb: float
    index_size: int
    last_updated: datetime
    retention_days: int


class VectorStorageInterface(ABC):
    """Abstract interface for vector storage backends."""

    @abstractmethod
    async def store_context(
        self,
        context_id: str,
        context: Context,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store a context with its embedding."""
        pass

    @abstractmethod
    async def get_context(self, context_id: str) -> Optional[Context]:
        """Retrieve a context by ID."""
        pass

    @abstractmethod
    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar contexts by embedding."""
        pass

    @abstractmethod
    async def delete_context(self, context_id: str) -> bool:
        """Delete a context by ID."""
        pass

    @abstractmethod
    async def update_context(
        self,
        context_id: str,
        context: Context,
        embedding: Optional[List[float]] = None
    ) -> bool:
        """Update an existing context."""
        pass

    @abstractmethod
    async def get_stats(self) -> StorageStats:
        """Get storage statistics."""
        pass


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-based embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self._dimension = None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except ImportError:
            raise ImportError("Please install openai package: pip install openai")
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the model."""
        if self._dimension is None:
            dimensions = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536
            }
            self._dimension = dimensions.get(self.model, 1536)
        return self._dimension


class ChromaStorage(VectorStorageInterface):
    """ChromaDB implementation of vector storage."""

    def __init__(
        self,
        collection_name: str = "context_collection",
        persist_directory: str = "./chroma_db",
        embedding_dimension: int = 1536
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_dimension = embedding_dimension
        self._client = None
        self._collection = None

    def _get_client(self):
        """Get or create ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=self.persist_directory)
            except ImportError:
                raise ImportError("Please install chromadb package: pip install chromadb")
        return self._client

    def _get_collection(self):
        """Get or create collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def store_context(
        self,
        context_id: str,
        context: Context,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store context in ChromaDB."""
        try:
            collection = self._get_collection()

            # Prepare metadata
            storage_metadata = {
                "context_id": context_id,
                "created_at": context.meta.created_at.isoformat(),
                "goal": context.meta.goal,
                "environment": context.meta.environment,
                "total_steps": len(context.runtime.execution_plan),
                "is_completed": context.runtime.is_completed
            }

            if metadata:
                storage_metadata.update(metadata)

            # Store the context data as JSON
            context_json = context.to_json()

            collection.add(
                embeddings=[embedding],
                documents=[context_json],
                metadatas=[storage_metadata],
                ids=[context_id]
            )

            return True
        except Exception as e:
            print(f"Failed to store context: {e}")
            return False

    async def get_context(self, context_id: str) -> Optional[Context]:
        """Retrieve context by ID."""
        try:
            collection = self._get_collection()
            result = collection.get(ids=[context_id])

            if result['documents'] and len(result['documents']) > 0:
                context_json = result['documents'][0]
                return Context.from_json(context_json)

            return None
        except Exception as e:
            print(f"Failed to retrieve context: {e}")
            return None

    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar contexts."""
        try:
            collection = self._get_collection()

            query_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=filters
            )

            results = []
            if query_results['ids'] and len(query_results['ids'][0]) > 0:
                for i, context_id in enumerate(query_results['ids'][0]):
                    similarity_score = 1.0 - query_results['distances'][0][i]  # Convert cosine distance to similarity
                    metadata = query_results['metadatas'][0][i]
                    context_json = query_results['documents'][0][i]

                    context = Context.from_json(context_json)
                    created_at = datetime.fromisoformat(metadata.get('created_at', '2024-01-01'))

                    result = SearchResult(
                        context_id=context_id,
                        similarity_score=similarity_score,
                        metadata=metadata,
                        context_data=context,
                        created_at=created_at
                    )
                    results.append(result)

            return results
        except Exception as e:
            print(f"Failed to search contexts: {e}")
            return []

    async def delete_context(self, context_id: str) -> bool:
        """Delete context by ID."""
        try:
            collection = self._get_collection()
            collection.delete(ids=[context_id])
            return True
        except Exception as e:
            print(f"Failed to delete context: {e}")
            return False

    async def update_context(
        self,
        context_id: str,
        context: Context,
        embedding: Optional[List[float]] = None
    ) -> bool:
        """Update existing context."""
        # Delete old and insert new
        await self.delete_context(context_id)
        if embedding is None:
            # Generate embedding from context goal and summary
            text_for_embedding = f"{context.meta.goal} {context.get_execution_summary()}"
            # This would need an embedding provider - for now use empty embedding
            embedding = [0.0] * self.embedding_dimension

        return await self.store_context(context_id, context, embedding)

    async def get_stats(self) -> StorageStats:
        """Get storage statistics."""
        try:
            collection = self._get_collection()
            count = collection.count()

            # Estimate storage size (rough approximation)
            storage_size_mb = count * 0.1  # Assume 100KB per context

            return StorageStats(
                total_contexts=count,
                storage_size_mb=storage_size_mb,
                index_size=count,
                last_updated=datetime.now(),
                retention_days=365
            )
        except Exception as e:
            print(f"Failed to get stats: {e}")
            return StorageStats(0, 0.0, 0, datetime.now(), 365)


class ContextRecorderConfig(BaseModel):
    """Configuration for Context Recorder."""

    storage_type: StorageType = Field(default=StorageType.CHROMA)
    storage_config: Dict[str, Any] = Field(default_factory=dict)
    embedding_config: Dict[str, Any] = Field(default_factory=dict)
    retention_days: int = Field(default=365, description="Days to retain contexts")
    auto_archive: bool = Field(default=True, description="Auto-archive completed contexts")
    index_new_contexts: bool = Field(default=True, description="Index new contexts automatically")
    batch_size: int = Field(default=100, description="Batch size for operations")
    enable_compression: bool = Field(default=True, description="Enable compression for storage")

    @validator('retention_days')
    def validate_retention_days(cls, v):
        if v < 1:
            raise ValueError("Retention days must be at least 1")
        return v

    @validator('batch_size')
    def validate_batch_size(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Batch size must be between 1 and 1000")
        return v


class ContextRecorder(BaseModel):
    """
    Main Context Recorder class.

    Provides persistent storage, retrieval, and search capabilities for Context objects
    using vector databases for semantic similarity search.
    """

    config: ContextRecorderConfig
    storage: VectorStorageInterface
    embedding_provider: EmbeddingProvider
    _index_lock: asyncio.Lock = Field(default_factory=asyncio.Lock)

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        config: Optional[ContextRecorderConfig] = None,
        storage: Optional[VectorStorageInterface] = None,
        embedding_provider: Optional[EmbeddingProvider] = None
    ):
        # Initialize with defaults
        if config is None:
            config = ContextRecorderConfig()

        if storage is None:
            storage = self._create_storage(config)

        if embedding_provider is None:
            embedding_provider = self._create_embedding_provider(config)

        super().__init__(
            config=config,
            storage=storage,
            embedding_provider=embedding_provider
        )

    @staticmethod
    def _create_storage(config: ContextRecorderConfig) -> VectorStorageInterface:
        """Create storage instance based on configuration."""
        storage_config = config.storage_config

        if config.storage_type == StorageType.CHROMA:
            return ChromaStorage(
                collection_name=storage_config.get("collection_name", "context_collection"),
                persist_directory=storage_config.get("persist_directory", "./chroma_db"),
                embedding_dimension=storage_config.get("embedding_dimension", 1536)
            )
        else:
            raise ValueError(f"Storage type {config.storage_type} not yet implemented")

    @staticmethod
    def _create_embedding_provider(config: ContextRecorderConfig) -> EmbeddingProvider:
        """Create embedding provider based on configuration."""
        embedding_config = config.embedding_config

        if embedding_config.get("provider") == "openai":
            return OpenAIEmbeddingProvider(
                api_key=embedding_config["api_key"],
                model=embedding_config.get("model", "text-embedding-3-small")
            )
        else:
            # Default to OpenAI with environment variables
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found in environment variables")

            return OpenAIEmbeddingProvider(api_key=api_key)

    async def archive_context(
        self,
        context: Context,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Archive a context to persistent storage.

        Args:
            context: Context to archive
            metadata: Additional metadata to store

        Returns:
            Context ID for the archived context
        """
        async with self._index_lock:
            # Generate unique ID
            context_id = str(uuid.uuid4())

            # Generate embedding for semantic search
            text_for_embedding = self._prepare_text_for_embedding(context)
            embedding = await self.embedding_provider.generate_embedding(text_for_embedding)

            # Store context
            success = await self.storage.store_context(
                context_id=context_id,
                context=context,
                embedding=embedding,
                metadata=metadata
            )

            if not success:
                raise RuntimeError(f"Failed to archive context {context_id}")

            return context_id

    async def retrieve_context(self, context_id: str) -> Optional[Context]:
        """
        Retrieve a context by ID.

        Args:
            context_id: ID of the context to retrieve

        Returns:
            Retrieved context or None if not found
        """
        return await self.storage.get_context(context_id)

    async def search_similar_contexts(
        self,
        query: str,
        limit: int = 10,
        search_type: SearchType = SearchType.SEMANTIC,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.5
    ) -> List[SearchResult]:
        """
        Search for similar contexts.

        Args:
            query: Search query
            limit: Maximum number of results
            search_type: Type of search to perform
            filters: Metadata filters
            min_similarity: Minimum similarity score threshold

        Returns:
            List of search results
        """
        # Generate embedding for query
        query_embedding = await self.embedding_provider.generate_embedding(query)

        # Perform similarity search
        results = await self.storage.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            filters=filters
        )

        # Filter by similarity threshold
        filtered_results = [
            result for result in results
            if result.similarity_score >= min_similarity
        ]

        # Sort by similarity score (descending)
        filtered_results.sort(key=lambda x: x.similarity_score, reverse=True)

        return filtered_results

    async def batch_archive_contexts(
        self,
        contexts: List[Context],
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Archive multiple contexts in batch.

        Args:
            contexts: List of contexts to archive
            metadata_list: List of metadata for each context

        Returns:
            List of context IDs for archived contexts
        """
        context_ids = []

        # Process in batches
        batch_size = self.config.batch_size
        for i in range(0, len(contexts), batch_size):
            batch = contexts[i:i + batch_size]
            batch_metadata = metadata_list[i:i + batch_size] if metadata_list else [None] * len(batch)

            # Generate embeddings in batch
            texts = [self._prepare_text_for_embedding(ctx) for ctx in batch]
            embeddings = await self.embedding_provider.generate_batch_embeddings(texts)

            # Store each context
            for context, embedding, metadata in zip(batch, embeddings, batch_metadata):
                context_id = str(uuid.uuid4())

                success = await self.storage.store_context(
                    context_id=context_id,
                    context=context,
                    embedding=embedding,
                    metadata=metadata
                )

                if success:
                    context_ids.append(context_id)

        return context_ids

    async def delete_archived_context(self, context_id: str) -> bool:
        """
        Delete an archived context.

        Args:
            context_id: ID of the context to delete

        Returns:
            True if deleted successfully
        """
        return await self.storage.delete_context(context_id)

    async def cleanup_old_contexts(self, days_to_keep: Optional[int] = None) -> int:
        """
        Clean up old contexts based on retention policy.

        Args:
            days_to_keep: Number of days to keep (overrides config)

        Returns:
            Number of contexts deleted
        """
        # This would require implementing date-based queries in storage
        # For now, return 0 as placeholder
        return 0

    def _prepare_text_for_embedding(self, context: Context) -> str:
        """
        Prepare text representation of context for embedding.

        Args:
            context: Context to prepare

        Returns:
            Text string for embedding generation
        """
        # Combine goal, execution summary, and key memory entries
        summary = context.get_execution_summary()

        text_parts = [
            context.meta.goal,
            f"Environment: {context.meta.environment}",
            f"Total steps: {summary['total_steps']}",
            f"Completed: {summary['completed_steps']}"
        ]

        # Add recent memory entries
        if context.history.short_term_memory:
            text_parts.extend(context.history.short_term_memory[-3:])  # Last 3 memory entries

        # Add recent action descriptions
        recent_actions = context.history.get_recent_actions(limit=5)
        for action in recent_actions:
            text_parts.append(f"Action: {action.action}")

        return " ".join(text_parts)

    async def get_storage_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            Storage statistics
        """
        return await self.storage.get_stats()

    async def update_archived_context(
        self,
        context_id: str,
        context: Context
    ) -> bool:
        """
        Update an existing archived context.

        Args:
            context_id: ID of the context to update
            context: Updated context

        Returns:
            True if updated successfully
        """
        return await self.storage.update_context(context_id, context)

    async def export_contexts(
        self,
        output_format: str = "json",
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Export contexts to a file.

        Args:
            output_format: Export format (json, csv)
            filters: Filters to apply

        Returns:
            Path to exported file
        """
        # This would require implementing query functionality in storage
        # For now, return placeholder
        export_path = f"contexts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
        # TODO: Implement actual export functionality
        return export_path