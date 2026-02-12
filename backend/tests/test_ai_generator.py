"""Tests for AIGenerator.

Tests the generate_response() method at line 49 with mocked Anthropic client.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_generator import AIGenerator


class TestAIGeneratorBasicResponse:
    """Test basic response generation without tools"""

    def test_generate_response_without_tools(self, mock_anthropic_client):
        """Basic response without tool usage"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")

            response = generator.generate_response(query="What is Python?")

            assert response == "This is a test response about machine learning."
            mock_anthropic_client.messages.create.assert_called_once()

    def test_generate_response_includes_query(self, mock_anthropic_client):
        """Query is passed to the API"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")

            generator.generate_response(query="Explain neural networks")

            call_args = mock_anthropic_client.messages.create.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert "Explain neural networks" in messages[0]["content"]

    def test_generate_response_uses_system_prompt(self, mock_anthropic_client):
        """System prompt is included in API call"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")

            generator.generate_response(query="test query")

            call_args = mock_anthropic_client.messages.create.call_args
            system = call_args.kwargs["system"]
            assert "course materials" in system.lower() or "educational" in system.lower()


class TestAIGeneratorWithHistory:
    """Test response generation with conversation history"""

    def test_generate_response_with_history(self, mock_anthropic_client):
        """History is included in system prompt"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")
            history = "User: What is ML?\nAssistant: Machine Learning is..."

            generator.generate_response(
                query="Tell me more",
                conversation_history=history
            )

            call_args = mock_anthropic_client.messages.create.call_args
            system = call_args.kwargs["system"]
            assert "Previous conversation" in system
            assert history in system

    def test_generate_response_without_history(self, mock_anthropic_client):
        """No history results in base system prompt only"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")

            generator.generate_response(query="test", conversation_history=None)

            call_args = mock_anthropic_client.messages.create.call_args
            system = call_args.kwargs["system"]
            assert "Previous conversation" not in system


class TestAIGeneratorWithTools:
    """Test response generation with tools"""

    def test_generate_response_passes_tools(self, mock_anthropic_client):
        """Tools are passed to API when provided"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")
            tools = [{
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}}
            }]

            generator.generate_response(query="test", tools=tools)

            call_args = mock_anthropic_client.messages.create.call_args
            assert "tools" in call_args.kwargs
            assert call_args.kwargs["tools"] == tools
            assert call_args.kwargs["tool_choice"] == {"type": "auto"}

    def test_generate_response_without_tools_no_tool_params(self, mock_anthropic_client):
        """No tools means no tool parameters in API call"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-test")

            generator.generate_response(query="test", tools=None)

            call_args = mock_anthropic_client.messages.create.call_args
            assert "tools" not in call_args.kwargs


class TestAIGeneratorToolExecution:
    """Test tool execution flow"""

    def test_handle_tool_execution(self, mock_anthropic_client_with_tool_use, mock_tool_manager):
        """Tool calls are executed correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_with_tool_use):
            generator = AIGenerator(api_key="test_key", model="claude-test")
            tools = [{"name": "search_course_content", "description": "Search"}]

            response = generator.generate_response(
                query="What is machine learning?",
                tools=tools,
                tool_manager=mock_tool_manager
            )

            # Tool manager should have been called
            mock_tool_manager.execute_tool.assert_called_once()
            # Final response should be returned
            assert "machine learning" in response.lower()

    def test_tool_results_formatted_correctly(self, mock_anthropic_client_with_tool_use, mock_tool_manager):
        """Tool results are formatted correctly for follow-up"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_with_tool_use):
            generator = AIGenerator(api_key="test_key", model="claude-test")
            tools = [{"name": "search_course_content", "description": "Search"}]

            generator.generate_response(
                query="test query",
                tools=tools,
                tool_manager=mock_tool_manager
            )

            # Check second API call (follow-up after tool execution)
            assert mock_anthropic_client_with_tool_use.messages.create.call_count == 2
            second_call = mock_anthropic_client_with_tool_use.messages.create.call_args_list[1]
            messages = second_call.kwargs["messages"]

            # Should have user message, assistant tool_use, and user tool_result
            assert len(messages) == 3
            assert messages[2]["role"] == "user"
            # Tool results are in a list
            tool_results = messages[2]["content"]
            assert isinstance(tool_results, list)
            assert tool_results[0]["type"] == "tool_result"

    def test_final_response_after_tools(self, mock_anthropic_client_with_tool_use, mock_tool_manager):
        """Returns synthesized answer after tool execution"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_with_tool_use):
            generator = AIGenerator(api_key="test_key", model="claude-test")
            tools = [{"name": "search_course_content", "description": "Search"}]

            response = generator.generate_response(
                query="test query",
                tools=tools,
                tool_manager=mock_tool_manager
            )

            # Should return the final response text
            assert response == "Based on the course materials, machine learning is..."


class TestAIGeneratorConfiguration:
    """Test AIGenerator configuration"""

    def test_uses_provided_model(self, mock_anthropic_client):
        """Generator uses the provided model"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="claude-custom-model")

            generator.generate_response(query="test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["model"] == "claude-custom-model"

    def test_uses_configured_temperature(self, mock_anthropic_client):
        """Generator uses temperature 0 for deterministic responses"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="test-model")

            generator.generate_response(query="test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["temperature"] == 0

    def test_uses_configured_max_tokens(self, mock_anthropic_client):
        """Generator uses configured max tokens"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test_key", model="test-model")

            generator.generate_response(query="test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["max_tokens"] == 800


class TestAIGeneratorSystemPrompt:
    """Test system prompt content"""

    def test_system_prompt_contains_key_instructions(self):
        """System prompt has required instruction elements"""
        prompt = AIGenerator.SYSTEM_PROMPT

        # Should mention tool usage
        assert "search" in prompt.lower() or "tool" in prompt.lower()
        # Should mention educational/course context
        assert "course" in prompt.lower() or "educational" in prompt.lower()
        # Should mention conciseness
        assert "concise" in prompt.lower() or "brief" in prompt.lower()

    def test_system_prompt_mentions_one_search_limit(self):
        """System prompt mentions one search per query limit"""
        prompt = AIGenerator.SYSTEM_PROMPT

        assert "one search" in prompt.lower() or "single search" in prompt.lower() or "maximum" in prompt.lower()
