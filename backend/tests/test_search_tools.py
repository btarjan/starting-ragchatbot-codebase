"""Tests for CourseSearchTool and ToolManager.

Tests the search tool's execute() method and source tracking behavior.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() at line 53"""

    def test_execute_with_valid_results(self, mock_vector_store, sample_search_results):
        """Verify formatted output when search returns results"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="machine learning")

        assert "Machine Learning Basics" in result
        assert "Lesson 1" in result or "Lesson 2" in result
        mock_vector_store.search.assert_called_once_with(
            query="machine learning", course_name=None, lesson_number=None
        )

    def test_execute_with_empty_results(self, mock_vector_store, empty_search_results):
        """Returns 'No relevant content' when search yields no results"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_with_course_filter(self, mock_vector_store, sample_search_results):
        """course_name is passed to VectorStore correctly"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="neural networks", course_name="ML Basics")

        mock_vector_store.search.assert_called_once_with(
            query="neural networks", course_name="ML Basics", lesson_number=None
        )

    def test_execute_with_lesson_filter(self, mock_vector_store, sample_search_results):
        """lesson_number is passed to VectorStore correctly"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="introduction", lesson_number=1)

        mock_vector_store.search.assert_called_once_with(
            query="introduction", course_name=None, lesson_number=1
        )

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Both course_name and lesson_number passed correctly"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="deep learning", course_name="Advanced ML", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="deep learning", course_name="Advanced ML", lesson_number=3
        )

    def test_execute_with_error(self, mock_vector_store, error_search_results):
        """Error from VectorStore is propagated correctly"""
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test query")

        assert "Search error" in result
        assert "Database connection failed" in result

    def test_empty_results_with_course_filter_message(
        self, mock_vector_store, empty_search_results
    ):
        """Empty results message includes course filter info"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test", course_name="Specific Course")

        assert "No relevant content found" in result
        assert "Specific Course" in result

    def test_empty_results_with_lesson_filter_message(
        self, mock_vector_store, empty_search_results
    ):
        """Empty results message includes lesson filter info"""
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test", lesson_number=5)

        assert "No relevant content found" in result
        assert "lesson 5" in result


class TestCourseSearchToolSourceTracking:
    """Test source tracking in CourseSearchTool"""

    def test_format_results_populates_sources(self, mock_vector_store, sample_search_results):
        """last_sources is populated after formatting results"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="machine learning")

        assert len(tool.last_sources) > 0
        # Check structure of sources
        for source in tool.last_sources:
            assert "display_text" in source
            assert "url" in source

    def test_sources_include_course_and_lesson(self, mock_vector_store, sample_search_results):
        """Sources include course title and lesson number"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="machine learning")

        source_texts = [s["display_text"] for s in tool.last_sources]
        # Should have at least one source with lesson info
        has_lesson_info = any("Lesson" in text for text in source_texts)
        assert has_lesson_info

    def test_sources_deduplicated(self, mock_vector_store):
        """Duplicate sources are removed"""
        # Create results with duplicate courses
        results = SearchResults(
            documents=["Content 1", "Content 2", "Content 3"],
            metadata=[
                {"course_title": "Same Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "Same Course", "lesson_number": 1, "chunk_index": 1},
                {"course_title": "Same Course", "lesson_number": 1, "chunk_index": 2},
            ],
            distances=[0.1, 0.2, 0.3],
        )
        mock_vector_store.search.return_value = results
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        # Should only have one source despite 3 results from same course/lesson
        assert len(tool.last_sources) == 1

    def test_sources_replaced_on_new_search_with_results(
        self, mock_vector_store, sample_search_results
    ):
        """Sources are replaced when new search returns results"""
        tool = CourseSearchTool(mock_vector_store)

        # First search with results
        tool.execute(query="first search")
        first_sources = tool.last_sources.copy()
        assert len(first_sources) > 0

        # Second search with different results
        new_results = SearchResults(
            documents=["New content from different course"],
            metadata=[{"course_title": "Different Course", "lesson_number": 5, "chunk_index": 0}],
            distances=[0.1],
        )
        mock_vector_store.search.return_value = new_results
        tool.execute(query="second search")

        # Sources should be from the new search
        assert len(tool.last_sources) == 1
        assert "Different Course" in tool.last_sources[0]["display_text"]

    def test_url_lookup_called_for_lessons(self, mock_vector_store, sample_search_results):
        """get_lesson_link is called for results with lesson numbers"""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        # Should have called get_lesson_link for results with lesson_number
        assert mock_vector_store.get_lesson_link.called


class TestToolManager:
    """Test ToolManager registration and execution"""

    def test_tool_registration(self, mock_vector_store):
        """Tools can be registered correctly"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(search_tool)

        assert "search_course_content" in manager.tools

    def test_tool_definitions_correct(self, mock_vector_store):
        """Tool definitions are retrieved correctly"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
        assert "input_schema" in definitions[0]

    def test_execute_tool_calls_correct_tool(self, mock_vector_store, sample_search_results):
        """execute_tool calls the correct registered tool"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        result = manager.execute_tool("search_course_content", query="test query")

        assert result is not None
        mock_vector_store.search.assert_called()

    def test_execute_unknown_tool_returns_error(self):
        """Executing unknown tool returns error message"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", param="value")

        assert "not found" in result.lower()

    def test_get_last_sources_from_search_tool(self, mock_vector_store, sample_search_results):
        """get_last_sources retrieves sources from search tool"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        # Execute search to populate sources
        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert len(sources) > 0

    def test_reset_sources_clears_all_tools(self, mock_vector_store, sample_search_results):
        """reset_sources clears sources from all tools"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        # Execute search to populate sources
        manager.execute_tool("search_course_content", query="test")
        assert len(search_tool.last_sources) > 0

        # Reset sources
        manager.reset_sources()

        assert search_tool.last_sources == []
        assert manager.get_last_sources() == []

    def test_multiple_tools_registered(self, mock_vector_store):
        """Multiple tools can be registered"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)

        manager.register_tool(search_tool)
        manager.register_tool(outline_tool)

        definitions = manager.get_tool_definitions()
        assert len(definitions) == 2
        tool_names = [d["name"] for d in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names


class TestCourseSearchToolDefinition:
    """Test tool definition structure"""

    def test_tool_definition_has_required_fields(self, mock_vector_store):
        """Tool definition contains required Anthropic fields"""
        tool = CourseSearchTool(mock_vector_store)

        definition = tool.get_tool_definition()

        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition

    def test_input_schema_has_query_required(self, mock_vector_store):
        """Query is a required parameter"""
        tool = CourseSearchTool(mock_vector_store)

        definition = tool.get_tool_definition()
        schema = definition["input_schema"]

        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    def test_input_schema_has_optional_filters(self, mock_vector_store):
        """course_name and lesson_number are optional parameters"""
        tool = CourseSearchTool(mock_vector_store)

        definition = tool.get_tool_definition()
        schema = definition["input_schema"]

        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        # These should NOT be required
        assert "course_name" not in schema.get("required", [])
        assert "lesson_number" not in schema.get("required", [])
