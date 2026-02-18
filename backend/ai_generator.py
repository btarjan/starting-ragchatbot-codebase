from typing import Any

import anthropic
from config import config


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Maximum 2 searches per query** - use additional searches when:
  - Comparing information across different courses
  - Question spans multiple topics requiring separate lookups
  - Initial results are insufficient for a complete answer
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Course Outline Tool Usage:
- Use the outline tool when users ask about course structure, syllabus, lesson lists, or what a course covers
- Returns: course title, course link, and complete lesson list (number + title for each)
- Examples: "What lessons are in the MCP course?", "Show me the outline for...", "What topics does this course cover?"

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **Course structure questions**: Use the outline tool
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: str | None = None,
        tools: list | None = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages with user query
        messages = [{"role": "user", "content": query}]
        round_count = 0

        while round_count < config.MAX_TOOL_ROUNDS:
            # Prepare API call parameters
            api_params = {**self.base_params, "messages": messages, "system": system_content}

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude
            response = self.client.messages.create(**api_params)

            # If not a tool use response, return the text
            if response.stop_reason != "tool_use" or not tool_manager:
                return response.content[0].text

            # Execute tools and accumulate messages
            tool_results = self._execute_tools_from_response(response, tool_manager)

            # Add assistant's tool use response
            messages.append({"role": "assistant", "content": response.content})

            # Add tool results as user message
            messages.append({"role": "user", "content": tool_results})

            round_count += 1

        # Max rounds reached - final call WITHOUT tools to force a response
        final_params = {**self.base_params, "messages": messages, "system": system_content}

        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _execute_tools_from_response(self, response, tool_manager) -> list[dict[str, Any]]:
        """
        Execute all tool calls from a response and return tool results.

        Args:
            response: The response containing tool use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool_result dicts ready to be added to messages
        """
        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                except Exception as e:
                    tool_result = f"Tool execution error: {str(e)}"

                tool_results.append(
                    {"type": "tool_result", "tool_use_id": content_block.id, "content": tool_result}
                )

        return tool_results
