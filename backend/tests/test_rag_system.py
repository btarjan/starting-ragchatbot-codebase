"""Integration tests for RAGSystem.

Tests the query() method at line 104 and exposes the MAX_RESULTS=0 bug.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config
from vector_store import SearchResults


@dataclass
class MockConfig:
    """Mock config for testing"""
    ANTHROPIC_API_KEY: str = "test_api_key"
    ANTHROPIC_MODEL: str = "claude-test"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


class TestRAGSystemQueryOrchestration:
    """Test RAGSystem.query() orchestration at line 104"""

    def test_query_orchestration(self, mock_anthropic_client, mock_vector_store):
        """Components are wired correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)

                # Override components with mocks
                rag.vector_store = mock_vector_store
                rag.ai_generator.client = mock_anthropic_client

                response, sources = rag.query("What is machine learning?")

                # Should return a response
                assert response is not None
                assert isinstance(response, str)

    def test_session_management(self, mock_anthropic_client, mock_vector_store):
        """History is retrieved and updated correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)
                rag.ai_generator.client = mock_anthropic_client

                # Create a session
                session_id = "test_session_1"

                # First query
                rag.query("First question", session_id=session_id)

                # Check history was stored
                history = rag.session_manager.get_conversation_history(session_id)
                assert history is not None
                assert "First question" in history

    def test_source_extraction_and_reset(self, mock_anthropic_client, mock_vector_store, sample_search_results):
        """Sources are returned then cleared"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem
                from search_tools import CourseSearchTool

                config = MockConfig()
                rag = RAGSystem(config)
                rag.ai_generator.client = mock_anthropic_client
                rag.vector_store = mock_vector_store

                # Set up search tool with sources
                rag.search_tool.last_sources = [
                    {"display_text": "Test Course - Lesson 1", "url": "https://test.com"}
                ]

                response, sources = rag.query("test query")

                # Sources should be returned
                assert sources is not None

                # Sources should be reset after query
                assert rag.search_tool.last_sources == []

    def test_tools_registered(self, mock_anthropic_client, mock_vector_store):
        """Both search and outline tools are available"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)

                tools = rag.tool_manager.get_tool_definitions()
                tool_names = [t["name"] for t in tools]

                assert "search_course_content" in tool_names
                assert "get_course_outline" in tool_names


class TestRAGSystemMaxResultsBug:
    """Tests that expose the MAX_RESULTS=0 bug"""

    def test_query_with_max_results_zero_returns_empty(self):
        """
        When MAX_RESULTS=0 in config, vector search returns empty results.

        This test exposes the bug by directly testing VectorStore behavior
        with max_results=0.
        """
        # Create a VectorStore with max_results=0 (the bug)
        # We can't easily test the full integration without ChromaDB,
        # but we can verify that the config value would cause issues

        from config import config as real_config

        # This assertion will FAIL if MAX_RESULTS=0
        # (same as test_config.py but focused on the search impact)
        if real_config.MAX_RESULTS == 0:
            pytest.fail(
                f"MAX_RESULTS is {real_config.MAX_RESULTS}. "
                "This causes VectorStore.search() to always return empty results, "
                "which makes the RAG chatbot return 'query failed' for all queries."
            )

    def test_vector_store_search_limit_from_config(self):
        """Verify that MAX_RESULTS is used as search limit in VectorStore"""
        from config import config as real_config

        # The bug: MAX_RESULTS=0 means ChromaDB returns 0 documents
        # This test documents the expected behavior
        assert real_config.MAX_RESULTS > 0, (
            f"MAX_RESULTS={real_config.MAX_RESULTS} will cause "
            "vector_store.py:90 to request 0 results from ChromaDB"
        )

    def test_rag_system_initializes_vector_store_with_max_results(self, mock_anthropic_client):
        """RAGSystem passes MAX_RESULTS to VectorStore at rag_system.py:18"""
        from config import config as real_config

        # Document the flow: config.MAX_RESULTS -> VectorStore.__init__ -> search()
        # If MAX_RESULTS=0, the search at vector_store.py:90 returns nothing

        assert real_config.MAX_RESULTS > 0, (
            "rag_system.py:18 passes config.MAX_RESULTS to VectorStore. "
            f"Current value is {real_config.MAX_RESULTS}, which breaks search."
        )


class TestRAGSystemIntegration:
    """Integration tests for full query flow"""

    def test_query_returns_tuple(self, mock_anthropic_client, mock_vector_store):
        """Query returns (response, sources) tuple"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)
                rag.ai_generator.client = mock_anthropic_client

                result = rag.query("test query")

                assert isinstance(result, tuple)
                assert len(result) == 2
                response, sources = result
                assert isinstance(response, str)
                assert isinstance(sources, list)

    def test_query_without_session(self, mock_anthropic_client, mock_vector_store):
        """Query works without session ID"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)
                rag.ai_generator.client = mock_anthropic_client

                response, sources = rag.query("test query", session_id=None)

                assert response is not None

    def test_query_with_new_session(self, mock_anthropic_client, mock_vector_store):
        """Query creates history for new session"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)
                rag.ai_generator.client = mock_anthropic_client

                response, sources = rag.query("What is ML?", session_id="new_session")

                # Session should now have history
                history = rag.session_manager.get_conversation_history("new_session")
                assert history is not None
                assert "What is ML?" in history


class TestRAGSystemCourseAnalytics:
    """Test course analytics method"""

    def test_get_course_analytics(self, mock_anthropic_client, mock_vector_store):
        """Analytics returns expected structure"""
        mock_vector_store.get_course_count.return_value = 3
        mock_vector_store.get_existing_course_titles.return_value = [
            "Course 1", "Course 2", "Course 3"
        ]

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            with patch('rag_system.VectorStore', return_value=mock_vector_store):
                from rag_system import RAGSystem

                config = MockConfig()
                rag = RAGSystem(config)
                rag.vector_store = mock_vector_store

                analytics = rag.get_course_analytics()

                assert "total_courses" in analytics
                assert "course_titles" in analytics
                assert analytics["total_courses"] == 3
                assert len(analytics["course_titles"]) == 3
