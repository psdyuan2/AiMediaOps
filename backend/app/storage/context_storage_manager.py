"""
Context Storage Manager
Intelligent context splitting, storage, and retrieval functionality
"""

import os
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast
import logging
import hashlib
import uuid
from pydantic import BaseModel, Field

from app.utils.simple_config import get, get_int, get_bool, get_float, get_list
from app.core.llm import LLMService
from app.core.context import Context


# 日志器
logger = logging.getLogger(__name__)


class ContextBlock(BaseModel):
    """Context block data model"""
    id: str = Field(description="Unique block ID")
    timestamp: str = Field(description="Creation timestamp")
    summary: str = Field(description="Summary of content")
    keywords: List[str] = Field(default_factory=list, description="List of keywords")
    content: str = Field(description="Full content")
    relevance_score: float = Field(default=0.0, description="Relevance score")
    block_size_tokens: int = Field(description="Block size in tokens")
    file_path: str = Field(description="Storage file path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchQuery(BaseModel):
    """Search query model"""
    query: str = Field(description="Search query string")
    time_window: str = Field(default="24h", description="Time window for search")
    search_type: str = Field(default="summary", description="Type of search")
    limit: int = Field(default=10, description="Maximum number of results")
    include_full_content: bool = Field(default=False, description="Whether to include full content")


class SearchResult(BaseModel):
    """Search result model"""
    block_id: str = Field(description="Block ID")
    file_path: str = Field(description="File path")
    timestamp: str = Field(description="Creation timestamp")
    summary: str = Field(description="Content summary")
    relevance_score: float = Field(description="Relevance score")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    content_preview: str = Field(description="Content preview")
    full_content: Optional[str] = Field(default=None, description="Full content")


class BlockSummary(BaseModel):
    """Block summary data model"""
    block_id: str = Field(description="Block ID")
    timestamp: str = Field(description="Creation timestamp")
    filename: str = Field(description="Filename")
    summary: str = Field(description="Content summary")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    token_count: int = Field(description="Token count")
    block_count: int = Field(description="Number of blocks")
    time_range: str = Field(description="Time range")


class IContextStorage:
    """Abstract interface for context storage"""
    async def get_available_directories(self) -> Dict[str, Any]:
        """Get available context directories within time range"""
        raise NotImplementedError

    async def search_by_filename(self, filename_pattern: str) -> List[SearchResult]:
        """Search context blocks by filename pattern"""
        raise NotImplementedError

    async def search_by_keywords(self, keywords: List[str], time_range: str = "24h") -> List[SearchResult]:
        """Search context blocks by keywords"""
        raise NotImplementedError

    async def load_context_blocks(self, block_ids: List[str]) -> List[ContextBlock]:
        """Load full context blocks by IDs"""
        raise NotImplementedError

    async def store_current_state(self, context: Context) -> str:
        """Store current context state as a new block"""
        raise NotImplementedError


class BlockNaming:
    """Intelligent file naming for context blocks"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count of text (simple approximation)"""
        # Simple estimation: Chinese chars ≈ 0.5 token, English words ≈ 4-7 tokens
        chinese_chars = len(text)
        english_words = len(text.split())
        return int(chinese_chars * 0.5 + english_words * 4)

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename by removing special characters"""
        remove_chars = get('CONTEXT_STORAGE_REMOVE_CHARS', "!@#$%^&*()+=[]{}|\\:;\"'<>?,./")
        replace_with_underscore = get('CONTEXT_STORAGE_REPLACE_WITH_UNDERSCORE', " -")

        sanitized = name
        for char in remove_chars:
            sanitized = sanitized.replace(char, "")

        for char in replace_with_underscore:
            sanitized = sanitized.replace(char, "_")
        return sanitized[:50]  # Limit max length

    async def _generate_llm_name(self, content_summary: str) -> str:
        """Generate English name using LLM"""
        if not self.llm_service:
            # Fallback to simple keyword extraction if no LLM service
            words = content_summary.split()[:3]
            return "_".join(words) if words else "untitled"

        try:
            from pydantic import BaseModel

            class LLMNameResponse(BaseModel):
                english_name: str = Field(description="English name generated from content")
                confidence: float = Field(default=0.8, description="Confidence score")

            prompt = f"""
Based on the following content, generate a concise English name (3-5 words) suitable for a filename:

Content: {content_summary[:500]}...

Requirements:
1. Use simple, common English words
2. Connect words with underscores (_)
3. Avoid special characters
4. Highlight the core topic
5. Maximum 5 words
6. Use lowercase letters only

Return only the English name, no explanations or markdown formatting.
            """.strip()

            response = await self.llm_service.generate(
                prompt=prompt,
                response_model=LLMNameResponse,
                system_prompt="You are a professional file naming assistant. Generate concise, accurate English filenames that clearly describe the content."
            )

            # Sanitize the generated name
            return self._sanitize_filename(response.english_name)

        except Exception as e:
            logger.warning(f"LLM name generation failed: {e}, falling back to simple naming")
            # Fallback to simple naming
            words = content_summary.split()[:3]
            return "_".join(words) if words else "untitled"

    async def generate_filename(self, content_summary: str, timestamp: datetime) -> str:
        """Generate filename for context block"""
        use_llm = get_bool('CONTEXT_STORAGE_USE_LLM_GENERATION', True)

        if use_llm:
            english_name = await self._generate_llm_name(content_summary)
        else:
            # Simple keyword extraction
            words = content_summary.split()[:3]
            english_name = "_".join(words) if words else "untitled"

        cleaned_name = self._sanitize_filename(english_name)
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H%M")

        max_length = get_int('CONTEXT_STORAGE_MAX_LENGTH', 50)
        if len(cleaned_name) > max_length:
            cleaned_name = cleaned_name[:max_length]

        return f"{timestamp_str}_{cleaned_name}"

    def create_file_path(self, filename: str, storage_root: Path) -> Path:
        """Create full file path"""
        return storage_root / "blocks" / f"{filename}.json"


class SimpleContextStorage(IContextStorage):
    """Simple SQLite implementation for context storage"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.storage_root = Path(get('CONTEXT_STORAGE_ROOT', 'context_storage'))
        self.db_path = self.storage_root / "database" / get('CONTEXT_STORAGE_DB_PATH', 'context_blocks.db')
        self.block_naming = BlockNaming(llm_service=llm_service)
        self.db: Optional[sqlite3.Connection] = None

        # Ensure directories exist
        self.storage_root.mkdir(parents=True, exist_ok=True)
        (self.storage_root / "blocks").mkdir(parents=True, exist_ok=True)
        (self.storage_root / "database").mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        logger.info(f"✅ ContextStorage initialized with root: {self.storage_root}")

    def _init_database(self):
        """Initialize SQLite database"""
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row

        # Create tables
        self._create_tables()

        logger.debug(f"🗄️ Database initialized at: {self.db_path}")

    def _create_tables(self):
        """Create database tables"""
        if not self.db:
            raise RuntimeError("Database not initialized")

        cursor = self.db.cursor()

        # Context blocks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS context_blocks (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            summary TEXT NOT NULL,
            keywords TEXT,
            content TEXT NOT NULL,
            relevance_score REAL DEFAULT 0.0,
            block_size_tokens INTEGER,
            file_path TEXT NOT NULL,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Keyword index table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_index (
            keyword TEXT NOT NULL,
            block_id TEXT NOT NULL,
            relevance REAL DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (keyword, block_id)
        )
        """)

        # Block summaries table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS block_summaries (
            block_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            filename TEXT NOT NULL,
            summary TEXT NOT NULL,
            keywords TEXT,
            token_count INTEGER,
            block_count INTEGER,
            time_range TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.db.commit()
        logger.info("🗄️ Database tables created successfully")

    def _estimate_text_tokens(self, text: str) -> int:
        """Estimate token count of text"""
        return len(text) // 2  # Simple estimation

    async def get_available_directories(self) -> Dict[str, Any]:
        """Get available context directories within time range"""
        if not self.db:
            return {}

        cursor = self.db.cursor()

        try:
            cursor.execute("""
            SELECT time_range,
                   COUNT(DISTINCT block_id) as block_count,
                   MIN(created_at) as earliest,
                   MAX(created_at) as latest
            FROM block_summaries
            GROUP BY time_range
            ORDER BY MIN(created_at)
            """)

            directories = {}
            for row in cursor.fetchall():
                time_range, block_count, earliest, latest = row
                directories[time_range] = {
                    "block_count": block_count,
                    "earliest_time": earliest,
                    "latest_time": latest,
                    "time_range_hours": self._parse_time_range(time_range)
                }

            return {
                "directories": directories,
                "storage_root": str(self.storage_root),
                "db_type": get('CONTEXT_STORAGE_DB_TYPE', 'sqlite')
            }

        except Exception as e:
            logger.error(f"❌ Error getting directories: {e}")
            return {}

    def _parse_time_range(self, time_range: str) -> str:
        """Parse time range string"""
        mapping = {
            "1h": "1 hour",
            "6h": "6 hours",
            "24h": "24 hours",
            "7d": "7 days",
            "30d": "30 days"
        }
        return mapping.get(time_range, time_range)

    async def search_by_filename(self, filename_pattern: str) -> List[SearchResult]:
        """Search context blocks by filename pattern"""
        if not self.db:
            return []

        cursor = self.db.cursor()

        try:
            cursor.execute("""
                SELECT id, file_path, timestamp, summary, relevance_score, keywords, content
                FROM context_blocks
                WHERE file_path LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (f"%{filename_pattern}%",))

            results = []
            for row in cursor.fetchall():
                results.append(SearchResult(
                    block_id=row[0],
                    file_path=row[1],
                    timestamp=row[2],
                    summary=row[3],
                    relevance_score=row[4] or 0.0,
                    keywords=json.loads(row[5]) if row[5] else [],
                    content_preview=row[6][:200] + "..." if len(row[6]) > 200 else row[6]
                ))

            return results

        except Exception as e:
            logger.error(f"❌ Error searching by filename: {e}")
            return []

    async def search_by_keywords(self, keywords: List[str], time_range: str = "24h") -> List[SearchResult]:
        """Search context blocks by keywords"""
        if not self.db:
            return []

        if not keywords:
            return []

        cursor = self.db.cursor()

        try:
            keyword = keywords[0]  # Use the first keyword for now (can be extended)
            cursor.execute("""
                SELECT id, file_path, timestamp, summary, relevance_score, keywords, content
                FROM context_blocks
                WHERE (content LIKE ? OR keywords LIKE ? OR summary LIKE ?)
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", get_int('CONTEXT_STORAGE_MAX_RESULTS', 10)))

            results = []
            for row in cursor.fetchall():
                results.append(SearchResult(
                    block_id=row[0],
                    file_path=row[1],
                    timestamp=row[2],
                    summary=row[3],
                    relevance_score=row[4] or 0.0,
                    keywords=json.loads(row[5]) if row[5] else [],
                    content_preview=row[6][:200] + "..." if len(row[6]) > 200 else row[6]
                ))

            return results

        except Exception as e:
            logger.error(f"❌ Error searching by keywords: {e}")
            return []

    async def load_context_blocks(self, block_ids: List[str]) -> List[ContextBlock]:
        """Load full context blocks by IDs"""
        if not self.db:
            return []

        if not block_ids:
            return []

        cursor = self.db.cursor()

        try:
            placeholders = ",".join(["?"] * len(block_ids))
            cursor.execute(f"""
                SELECT id, timestamp, summary, keywords, content, relevance_score,
                       block_size_tokens, file_path, metadata, created_at
                FROM context_blocks
                WHERE id IN ({placeholders})
                ORDER BY created_at
            """, block_ids)

            results = []
            for row in cursor.fetchall():
                results.append(ContextBlock(
                    id=row[0],
                    timestamp=row[1],
                    summary=row[2],
                    keywords=json.loads(row[3]) if row[3] else [],
                    content=row[4],
                    relevance_score=row[5] or 0.0,
                    block_size_tokens=row[6],
                    file_path=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                ))

            return results

        except Exception as e:
            logger.error(f"❌ Error loading context blocks: {e}")
            return []

    async def store_current_state(self, context: Context) -> str:
        """Store current context state as a new block"""
        if not self.db:
            logger.error("❌ Database not initialized")
            return ""

        cursor = self.db.cursor()

        try:
            # Prepare content for storage
            content_to_store = self._prepare_content_for_storage(context)

            if not content_to_store:
                logger.warning("⚠️ No content to store")
                return ""

            # Estimate token count
            token_count = self._estimate_text_tokens(content_to_store)

            # Generate filename
            timestamp = datetime.now()
            filename = await self.block_naming.generate_filename(content_to_store, timestamp)

            # Create file path
            file_path = self.block_naming.create_file_path(filename, self.storage_root)

            # Prepare metadata
            keywords = self._extract_keywords(content_to_store)
            progress = self._calculate_progress(context)

            metadata = {
                "agent_type": context.meta.goal.split()[0] if context.meta.goal else "Unknown",
                "context_id": context.meta.trace_id,
                "goal": context.meta.goal,
                "current_step_index": context.runtime.current_step_index,
                "total_steps": len(context.runtime.execution_plan),
                "progress_percentage": progress,
                "interrupt_flags": getattr(context.runtime, 'interrupt_flags', {}),
                "is_completed": getattr(context.runtime, 'is_completed', False)
            }

            # Extract keywords for indexing
            indexed_keywords = keywords[:10]  # Index at most 10 keywords

            # Prepare full content
            block_id = str(uuid.uuid4())
            full_content = {
                "id": block_id,
                "timestamp": timestamp.isoformat(),
                "summary": content_to_store[:200],  # Simple summary
                "keywords": keywords,
                "content": content_to_store,
                "relevance_score": 1.0,
                "block_size_tokens": token_count,
                "file_path": str(file_path),
                "metadata": metadata,
                "created_at": timestamp.isoformat()
            }

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(full_content, f, ensure_ascii=False, indent=2)

            # Store to database
            cursor.execute("""
                INSERT INTO context_blocks
                (id, timestamp, summary, keywords, content, relevance_score,
                 block_size_tokens, file_path, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                full_content["id"],
                full_content["timestamp"],
                full_content["summary"],
                json.dumps(indexed_keywords),
                full_content["content"],
                full_content["relevance_score"],
                full_content["block_size_tokens"],
                full_content["file_path"],
                json.dumps(metadata),
                full_content["created_at"]
            ))

            # Update keyword index
            for keyword in indexed_keywords:
                cursor.execute("""
                INSERT OR REPLACE INTO keyword_index
                (keyword, block_id, relevance, created_at)
                VALUES (?, ?, ?, ?)
                """, (keyword, full_content["id"], 1.0, full_content["created_at"]))

            self.db.commit()

            logger.info(f"✅ Context block stored: {filename} ({token_count} tokens)")
            return full_content["id"]

        except Exception as e:
            logger.error(f"❌ Error storing context state: {e}", exc_info=True)
            if self.db:
                self.db.rollback()
            return ""

    def _prepare_content_for_storage(self, context: Context) -> str:
        """Prepare content for storage"""
        content_parts = []

        # 1. Basic meta information
        content_parts.append(f"Goal: {context.meta.goal}")
        content_parts.append(f"Current Step: {context.runtime.current_step_index}")

        # 2. Execution history
        if context.history.action_log:
            content_parts.append(f"Recent Actions ({len(context.history.action_log)} total):")
            for i, log in enumerate(context.history.action_log[-5:]):  # Last 5 actions
                status = "✓" if log.result and log.result.get("success", True) else "✗"
                content_parts.append(f"  {i+1}. [{log.agent_name}] {log.action} - {status}")
                if log.result:
                    content_parts.append(f"     Result: {str(log.result)[:100]}")

        # 3. Interrupt flags
        if hasattr(context.runtime, 'interrupt_flags') and context.runtime.interrupt_flags:
            content_parts.append("Interrupt Flags:")
            for flag, value in context.runtime.interrupt_flags.items():
                content_parts.append(f"  {flag}: {value}")

        # 4. Execution plan progress
        total_steps = len(context.runtime.execution_plan)
        if total_steps > 0:
            progress = (context.runtime.current_step_index / total_steps) * 100
            content_parts.append(f"Progress: {progress:.1f}% ({context.runtime.current_step_index}/{total_steps})")

        # 5. Blackboard data (if any)
        if hasattr(context.runtime, 'blackboard') and context.runtime.blackboard:
            content_parts.append(f"Shared Data Keys: {list(context.runtime.blackboard.keys())}")

        return "\n".join(content_parts)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        words = text.split()
        keywords = []

        for word in words:
            word = word.strip("。，！？：；\"'()[]{}").lower()
            if len(word) >= 2:  # At least 2 characters
                keywords.append(word)

        # Deduplicate and limit
        return list(set(keywords))[:20]

    def _calculate_progress(self, context: Context) -> float:
        """Calculate progress percentage"""
        total_steps = len(context.runtime.execution_plan)
        if total_steps == 0:
            return 0.0
        return min(100.0, (context.runtime.current_step_index / total_steps) * 100)

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
            logger.info("🔒 Database connection closed")

    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Global instances
_context_storage: Optional[IContextStorage] = None
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
        logger.info("✅ LLMService instance created for ContextStorage")
    return _llm_service_instance


def get_context_storage() -> IContextStorage:
    """Get or create context storage instance"""
    global _context_storage
    if _context_storage is None:
        llm_service = get_llm_service()
        _context_storage = SimpleContextStorage(llm_service=llm_service)
        logger.info("✅ ContextStorage instance created")
    return _context_storage


def reset_context_storage():
    """Reset context storage instance (for testing)"""
    global _context_storage, _llm_service_instance
    if _context_storage:
        _context_storage.close()
    _context_storage = None
    _llm_service_instance = None
    logger.info("🔄 ContextStorage instances reset")
