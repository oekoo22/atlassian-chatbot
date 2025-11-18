"""Agent implementation for handling Product B specific requests."""

from __future__ import annotations

from typing import Any, Iterable, List

from openai import OpenAI
from config.settings import openai_key


class ProductAgentB:
    """Specialist agent focused on Product B support and guidance."""

    model: str = "gpt-4.1-mini"

    def __init__(self) -> None:
        self.client = OpenAI(api_key=openai_key)
        self.agent = self.client.agents.create(
            name="Product B Agent",
            description=(
                "Provides expert assistance for Product B usage, integrations, and "
                "diagnostics while keeping answers concise and actionable."
            ),
            instructions=(
                "You are the dedicated support agent for Product B. Focus on clear "
                "step-by-step help, reference Product B capabilities directly, and "
                "call out any configuration nuances users commonly overlook. Offer "
                "short summaries before detailed steps when helpful."
            ),
            model=self.model,
        )

    def answer_question(self, user_input: str) -> str:
        """Answer a user request about Product B via the Agents SDK."""

        thread = self.client.threads.create()
        run = self.client.threads.runs.create_and_poll(
            agent_id=self.agent.id,
            thread_id=thread.id,
            input=user_input,
        )

        messages = self.client.threads.messages.list(
            thread_id=thread.id, run_id=run.id
        )
        return self._extract_assistant_response(messages.data)

    def _extract_assistant_response(self, messages: Iterable[Any]) -> str:
        """Safely extract the assistant's textual reply from thread messages."""

        for message in messages:
            if getattr(message, "role", None) != "assistant":
                continue

            content_blocks: List[Any] = getattr(message, "content", [])
            text_parts = [
                block.text.value
                for block in content_blocks
                if getattr(block, "type", None) == "output_text"
                and hasattr(block, "text")
                and hasattr(block.text, "value")
            ]
            if text_parts:
                return "\n\n".join(text_parts)

        return ""

