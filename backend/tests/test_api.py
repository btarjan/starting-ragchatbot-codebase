"""API endpoint tests for FastAPI application.

Tests the FastAPI endpoints defined in app.py:
- POST /api/query (line 56)
- GET /api/courses (line 76)
- DELETE /api/sessions/{session_id} (line 88)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestQueryEndpoint:
    """Test POST /api/query endpoint"""

    def test_query_endpoint_success(self, test_client, mock_rag_system):
        """Successful query returns answer and sources"""
        # Mock RAG system response
        mock_rag_system.query.return_value = (
            "Machine learning is a subset of AI.",
            [{"display_text": "ML Course - Lesson 1", "url": "https://example.com/ml"}]
        )
        mock_rag_system.session_manager.create_session.return_value = "session_123"

        response = test_client.post(
            "/api/query",
            json={"query": "What is machine learning?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["answer"] == "Machine learning is a subset of AI."
        assert len(data["sources"]) == 1
        assert data["session_id"] == "session_123"

    def test_query_endpoint_with_existing_session(self, test_client, mock_rag_system):
        """Query with existing session_id maintains conversation history"""
        mock_rag_system.query.return_value = (
            "Deep learning uses neural networks.",
            []
        )

        response = test_client.post(
            "/api/query",
            json={
                "query": "What about deep learning?",
                "session_id": "existing_session_456"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing_session_456"

        # Verify RAG system was called with correct session
        mock_rag_system.query.assert_called_once_with(
            "What about deep learning?",
            "existing_session_456"
        )

    def test_query_endpoint_with_empty_query(self, test_client, mock_rag_system):
        """Empty query string is handled"""
        mock_rag_system.query.return_value = (
            "Please ask a question about the course materials.",
            []
        )
        mock_rag_system.session_manager.create_session.return_value = "session_789"

        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        assert response.status_code == 200
        # Empty query still gets processed (validation happens in RAG system)
        mock_rag_system.query.assert_called_once()

    def test_query_endpoint_invalid_json(self, test_client):
        """Malformed JSON returns 422"""
        response = test_client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_endpoint_missing_query_field(self, test_client):
        """Missing required 'query' field returns 422"""
        response = test_client.post(
            "/api/query",
            json={"session_id": "test"}  # Missing 'query' field
        )

        assert response.status_code == 422

    def test_query_endpoint_rag_system_error(self, test_client, mock_rag_system):
        """RAG system exceptions return 500"""
        mock_rag_system.query.side_effect = Exception("Vector store connection failed")

        response = test_client.post(
            "/api/query",
            json={"query": "test query"}
        )

        assert response.status_code == 500
        assert "Vector store connection failed" in response.json()["detail"]

    def test_query_endpoint_response_format(self, test_client, mock_rag_system):
        """Response matches QueryResponse schema"""
        mock_rag_system.query.return_value = (
            "Test answer",
            [
                {"display_text": "Course 1", "url": "https://example.com/1"},
                {"display_text": "Course 2", "url": None}  # Test with None URL
            ]
        )
        mock_rag_system.session_manager.create_session.return_value = "session_abc"

        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Validate source objects
        for source in data["sources"]:
            assert "display_text" in source
            assert "url" in source


class TestCoursesEndpoint:
    """Test GET /api/courses endpoint"""

    def test_courses_endpoint_success(self, test_client, mock_rag_system):
        """Successful request returns course statistics"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": [
                "Machine Learning Basics",
                "Advanced Deep Learning",
                "Computer Vision"
            ]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_courses_endpoint_empty_database(self, test_client, mock_rag_system):
        """Empty database returns zero courses"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_error(self, test_client, mock_rag_system):
        """Analytics error returns 500"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Database error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_courses_endpoint_response_format(self, test_client, mock_rag_system):
        """Response matches CourseStats schema"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Test Course"]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Validate types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        for title in data["course_titles"]:
            assert isinstance(title, str)


class TestSessionsEndpoint:
    """Test DELETE /api/sessions/{session_id} endpoint"""

    def test_clear_session_success(self, test_client, mock_rag_system):
        """Successful session clear returns status"""
        response = test_client.delete("/api/sessions/test_session_123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["session_id"] == "test_session_123"

        # Verify session was cleared
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "test_session_123"
        )

    def test_clear_session_with_special_characters(self, test_client, mock_rag_system):
        """Session ID with special characters is handled"""
        session_id = "session-with-dashes_and_underscores"
        response = test_client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_clear_nonexistent_session(self, test_client, mock_rag_system):
        """Clearing non-existent session succeeds (idempotent)"""
        # SessionManager.clear_session is idempotent
        response = test_client.delete("/api/sessions/nonexistent_session")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"


class TestErrorHandling:
    """Test error handling across endpoints"""

    def test_404_for_unknown_endpoint(self, test_client):
        """Unknown endpoint returns 404"""
        response = test_client.get("/api/unknown")
        assert response.status_code == 404

    def test_method_not_allowed(self, test_client):
        """Wrong HTTP method returns 405"""
        response = test_client.get("/api/query")  # Should be POST
        assert response.status_code == 405

    def test_internal_error_format(self, test_client, mock_rag_system):
        """500 errors return proper JSON format"""
        mock_rag_system.query.side_effect = Exception("Internal error")

        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)


class TestIntegrationFlow:
    """Test complete user flow across endpoints"""

    def test_full_conversation_flow(self, test_client, mock_rag_system):
        """Complete flow: query -> check courses -> clear session"""
        # Setup mocks
        mock_rag_system.session_manager.create_session.return_value = "flow_session"
        mock_rag_system.query.return_value = ("Answer 1", [])
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["Course A"]
        }

        # Step 1: Initial query (creates session)
        response1 = test_client.post(
            "/api/query",
            json={"query": "First question"}
        )
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Step 2: Follow-up query with same session
        response2 = test_client.post(
            "/api/query",
            json={"query": "Follow-up question", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Step 3: Check available courses
        response3 = test_client.get("/api/courses")
        assert response3.status_code == 200
        assert response3.json()["total_courses"] == 5

        # Step 4: Clear session
        response4 = test_client.delete(f"/api/sessions/{session_id}")
        assert response4.status_code == 200
        assert response4.json()["status"] == "cleared"

    def test_multiple_concurrent_sessions(self, test_client, mock_rag_system):
        """Multiple sessions can operate independently"""
        mock_rag_system.session_manager.create_session.side_effect = [
            "session_A",
            "session_B"
        ]
        mock_rag_system.query.return_value = ("Answer", [])

        # Create first session
        response1 = test_client.post(
            "/api/query",
            json={"query": "Question from user A"}
        )
        session_a = response1.json()["session_id"]

        # Create second session
        response2 = test_client.post(
            "/api/query",
            json={"query": "Question from user B"}
        )
        session_b = response2.json()["session_id"]

        # Sessions are independent
        assert session_a != session_b
        assert session_a == "session_A"
        assert session_b == "session_B"
