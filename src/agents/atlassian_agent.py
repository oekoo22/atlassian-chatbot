"""Agent runner that coordinates Atlassian tool calls through the OpenAI API."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

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
        self.agent = self.client.agents.create(
            model=self.model,
            instructions=(
                "You are a helpful assistant who searches and analyzes Jira tickets and "
                "Confluence pages. If the user asks for a specific ticket ID (e.g., SCRUM-3), use "
                "get_ticket_description. If the user searches for information about Confluence (e.g., "
                "'Find pages about XYZ'), use search_confluence_pages. If the user searches for ticket "
                "information (e.g., 'Where is XYZ mentioned?'), use search_tickets_by_keyword. "
                "Summarize the found information and respond in a clear and understandable manner. "
                "Please, always use the tools first before providing general information. When you "
                "found any information leading to an answer to the prompt, always just use the tools. "
                "You can also ask the user, if you can provide any additional information. Use your "
                "general knowledge JUST and ONLY JUST if the tools do not provide any information. If "
                "you are asked for information which you would clarify as some kind of organization "
                "intern information, e.g. vacation policies, internal structures, who is responsible "
                "for specific things etc., please NEVER answer with your general knowledge instead "
                "just use the tools to answer."
            ),
            tools=self.tools,
        )
        self.thread = self.client.threads.create()

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

        self.client.threads.messages.create(
            thread_id=self.thread.id, role="user", content=user_input
        )
        return self._run_agent()

    def _run_agent(self) -> str:
        """Execute the thread/run loop, submitting tool outputs until completion."""

        run = self.client.threads.runs.create(
            thread_id=self.thread.id, agent_id=self.agent.id
        )

        while True:
            if run.status == "requires_action" and run.required_action:
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    if function_name == "search_tickets_by_keyword":
                        result = self.search_tickets_by_keyword(arguments["keyword"])
                        output = json.dumps(result)
                    elif function_name == "search_confluence_pages":
                        result = self.search_confluence_pages(arguments["keyword"])
                        output = json.dumps(result)
                    elif function_name == "get_ticket_description":
                        output = self.get_ticket_description(arguments["ticket_id"])
                    else:
                        output = "Unsupported tool call"

                    tool_outputs.append({"tool_call_id": tool_call.id, "output": output})

                run = self.client.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=self.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs,
                )
                continue

            if run.status in {"completed", "failed", "cancelled", "expired"}:
                break

            run = self.client.threads.runs.poll(
                thread_id=self.thread.id, run_id=run.id
            )

        return self._extract_latest_assistant_response(run.id)

    def _extract_latest_assistant_response(self, run_id: Optional[str]) -> str:
        """Fetch the assistant's most recent text output for the given run."""

        messages = self.client.threads.messages.list(
            thread_id=self.thread.id, order="desc", limit=10
        )

        for message in messages.data:
            if message.role == "assistant" and (not run_id or message.run_id == run_id):
                text_parts = [
                    part.text.value
                    for part in message.content
                    if hasattr(part, "text") and part.text is not None
                ]
                return "".join(text_parts)

        return ""
