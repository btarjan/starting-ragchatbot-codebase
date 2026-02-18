"""Shared fixtures for RAG chatbot tests"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vector_store import SearchResults


@pytest.fixture
def sample_search_results():
    """Realistic SearchResults data for testing"""
    return SearchResults(
        documents=[
            "Course Introduction content: This lesson covers the basics of machine learning.",
            "Course Introduction content: Neural networks are computational models.",
            "Course Advanced Topics content: Deep learning uses multiple layers.",
        ],
        metadata=[
            {"course_title": "Machine Learning Basics", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Machine Learning Basics", "lesson_number": 2, "chunk_index": 1},
            {"course_title": "Advanced ML", "lesson_number": 1, "chunk_index": 0},
        ],
        distances=[0.1, 0.2, 0.3],
    )


@pytest.fixture
def empty_search_results():
    """Empty results for edge case testing"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Results with error message"""
    return SearchResults.empty("Search error: Database connection failed")


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mocked VectorStore with configurable results"""
    mock_store = MagicMock()
    mock_store.search.return_value = sample_search_results
    mock_store.get_course_link.return_value = "https://example.com/course"
    mock_store.get_lesson_link.return_value = "https://example.com/course/lesson1"
    return mock_store


@pytest.fixture
def mock_anthropic_client():
    """Mocked Anthropic client (no real API calls)"""
    mock_client = MagicMock()

    # Create a mock response for non-tool-use case
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [MagicMock(text="This is a test response about machine learning.")]

    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client_with_tool_use():
    """Mocked Anthropic client that triggers tool use"""
    mock_client = MagicMock()

    # Create tool use response
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "search_course_content"
    tool_use_block.id = "tool_123"
    tool_use_block.input = {"query": "machine learning basics"}

    initial_response = MagicMock()
    initial_response.stop_reason = "tool_use"
    initial_response.content = [tool_use_block]

    # Create final response after tool execution
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [
        MagicMock(text="Based on the course materials, machine learning is...")
    ]

    # First call returns tool_use, second returns final answer
    mock_client.messages.create.side_effect = [initial_response, final_response]

    return mock_client


@pytest.fixture
def mock_tool_manager():
    """Mocked ToolManager"""
    mock_manager = MagicMock()
    mock_manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]
    mock_manager.execute_tool.return_value = "Search results: Machine learning content..."
    mock_manager.get_last_sources.return_value = [
        {"display_text": "Machine Learning Basics - Lesson 1", "url": "https://example.com/ml"}
    ]
    return mock_manager


@pytest.fixture
def sample_course_metadata():
    """Sample course metadata for testing"""
    return {
        "title": "Machine Learning Basics",
        "instructor": "Dr. Smith",
        "course_link": "https://example.com/ml-course",
        "lesson_count": 5,
        "lessons_json": '[{"lesson_number": 1, "lesson_title": "Introduction", "lesson_link": "https://example.com/ml/1"}]',
    }


@pytest.fixture
def mock_anthropic_client_with_double_tool_use():
    """Mocked Anthropic client that triggers tool use twice before final response"""
    mock_client = MagicMock()

    # Create first tool use response
    tool_use_block_1 = MagicMock()
    tool_use_block_1.type = "tool_use"
    tool_use_block_1.name = "search_course_content"
    tool_use_block_1.id = "tool_123"
    tool_use_block_1.input = {"query": "machine learning basics"}

    first_response = MagicMock()
    first_response.stop_reason = "tool_use"
    first_response.content = [tool_use_block_1]

    # Create second tool use response
    tool_use_block_2 = MagicMock()
    tool_use_block_2.type = "tool_use"
    tool_use_block_2.name = "search_course_content"
    tool_use_block_2.id = "tool_456"
    tool_use_block_2.input = {"query": "deep learning advanced"}

    second_response = MagicMock()
    second_response.stop_reason = "tool_use"
    second_response.content = [tool_use_block_2]

    # Create final response after both tool executions
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [
        MagicMock(
            text="Comparing ML and DL: Machine learning covers basics while deep learning uses neural networks."
        )
    ]

    # First call returns tool_use, second returns tool_use, third returns final answer
    mock_client.messages.create.side_effect = [first_response, second_response, final_response]

    return mock_client


@pytest.fixture
def mock_anthropic_client_always_tool_use():
    """Mocked Anthropic client that always returns tool_use (for testing max rounds)"""
    mock_client = MagicMock()

    def create_tool_use_response(call_num):
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = f"tool_{call_num}"
        tool_use_block.input = {"query": f"query {call_num}"}

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [tool_use_block]
        return response

    # Create final response for when tools are removed
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [MagicMock(text="Final answer after max rounds reached.")]

    # First MAX_TOOL_ROUNDS calls return tool_use, then final call returns end_turn
    mock_client.messages.create.side_effect = [
        create_tool_use_response(1),
        create_tool_use_response(2),
        final_response,
    ]

    return mock_client
