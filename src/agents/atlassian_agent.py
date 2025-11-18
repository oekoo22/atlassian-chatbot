"""Agent runner that coordinates Atlassian tool calls through the OpenAI API."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from apis.confluence_api import ConfluenceAPI
from apis.jira_api import JiraAPI
from config.settings import openai_key


class AtlassianAgent:
    """Encapsulates the OpenAI Agent-style conversation loop."""

    model: str = "gpt-4o"

    def __init__(self) -> None:
        self.client = OpenAI(api_key=openai_key)
        self.jira_api = JiraAPI()
        self.confluence_api = ConfluenceAPI()
        self.messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant who searches and analyzes Jira tickets and "
                    "Confluence pages. If the user asks for a specific ticket ID (e.g., SCRUM-3), "
                    "use get_ticket_description. If the user searches for information about "
                    "Confluence (e.g., 'Find pages about XYZ'), use search_confluence_pages. If the "
                    "user searches for ticket information (e.g., 'Where is XYZ mentioned?'), use "
                    "search_tickets_by_keyword. Summarize the found information and respond in a "
                    "clear and understandable manner. Please, always use the tools first before "
                    "providing general information. When you found any information leading to an "
                    "answer to the prompt, always just use the tools. You can also ask the user, "
                    "if you can provide any additional information. Use your general knowledge JUST "
                    "and ONLY JUST if the tools do not provide any information. If you are asked for "
                    "information which you would clarify as some kind of organization intern "
                    "information, e.g. vacation policies, internal structures, who is responsible for "
                    "specific things etc., please NEVER answer with your general knowledge instead "
                    "just use the tools to answer."
                ),
            }
        ]
        self.tools: List[Dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "get_ticket_description",
                    "description": "Get the description of a specific Jira ticket using its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "The Jira ticket ID (e.g., SCRUM-3)",
                            }
                        },
                        "required": ["ticket_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_tickets_by_keyword",
                    "description": "Search for Jira tickets containing specific keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "The keyword to search for in tickets",
                            }
                        },
                        "required": ["keyword"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_confluence_pages",
                    "description": "Search for Confluence pages containing specific keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "The keyword to search for in Confluence pages",
                            }
                        },
                        "required": ["keyword"],
                    },
                },
            },
        ]

    def search_tickets_by_keyword(self, keyword: str) -> Any:
        """Proxy search against Jira for keyword matching."""

        return self.jira_api.search_tickets_by_keyword(keyword)

    def get_ticket_description(self, ticket_id: str) -> Any:
        """Get Jira ticket description."""

        return self.jira_api.get_ticket_description(ticket_id)

    def search_confluence_pages(self, keyword: str) -> Any:
        """Proxy search against Confluence for keyword matching."""

        return self.confluence_api.search_confluence_pages(keyword)

    def respond(self, user_input: str) -> str:
        """Run the Agent loop for the provided user input."""

        self.messages.append({"role": "user", "content": user_input})
        return self._complete_interaction()

    def _complete_interaction(self) -> str:
        """Request a completion and handle any tool calls until content is returned."""

        response = self.client.chat.completions.create(
            model=self.model, messages=self.messages, tools=self.tools
        )
        choice = response.choices[0]
        assistant_message = choice.message

        if choice.finish_reason == "tool_calls" and assistant_message.tool_calls:
            self._handle_tool_calls(assistant_message.tool_calls)
            return self._complete_interaction()

        self.messages.append({"role": "assistant", "content": assistant_message.content})
        return assistant_message.content or ""

    def _handle_tool_calls(self, tool_calls: List[Any]) -> None:
        """Dispatch tool calls returned by the model and append outputs to the conversation."""

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if function_name == "search_tickets_by_keyword":
                result = self.search_tickets_by_keyword(arguments["keyword"])
                content = json.dumps(result)
            elif function_name == "search_confluence_pages":
                result = self.search_confluence_pages(arguments["keyword"])
                content = json.dumps(result)
            elif function_name == "get_ticket_description":
                content = self.get_ticket_description(arguments["ticket_id"])
            else:
                content = "Unsupported tool call"

            self.messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
            self.messages.append({
                "role": "tool",
                "content": content,
                "tool_call_id": tool_call.id,
            })
