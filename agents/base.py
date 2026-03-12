"""BaseAgent - reusable ReAct loop with per-agent memory injection."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from openai import AsyncOpenAI

from services.memory import AgentMemory

logger = logging.getLogger("leetbot.agent")


@dataclass
class AgentResult:
    """Result from a ReAct agent run."""

    answer: str
    agent_name: str = ""
    tool_calls_made: list[dict] = field(default_factory=list)
    iterations: int = 0


ToolHandler = Callable[..., Coroutine[Any, Any, Any]]


class BaseAgent:
    """Domain-specific ReAct agent with isolated tools and memory.

    Subclasses set ``name``, ``system_prompt``, ``tool_definitions``, and
    implement ``execute_tool`` to dispatch tool calls to their service layer.
    """

    name: str = "base"
    system_prompt: str = "You are a helpful assistant."
    tool_definitions: list[dict] = []

    MEMORY_TOOL_DEFINITIONS: list[dict] = [
        {
            "type": "function",
            "function": {
                "name": "recall_memory",
                "description": "Retrieve your past conversations and saved preferences for this user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "The Discord user ID",
                        },
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_preference",
                "description": "Save a user preference for future reference (e.g. watchlist, username, preferred topics).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "The Discord user ID",
                        },
                        "key": {
                            "type": "string",
                            "description": "Preference key, e.g. 'watchlist', 'username'",
                        },
                        "value": {
                            "description": "Preference value (string, number, list, etc.)",
                        },
                    },
                    "required": ["user_id", "key", "value"],
                },
            },
        },
    ]

    def __init__(
        self,
        client: Optional[AsyncOpenAI],
        memory: AgentMemory,
        model: str = "gpt-4o-mini",
        max_iterations: int = 8,
    ):
        self.client = client
        self.memory = memory
        self.model = model
        self.max_iterations = max_iterations

    def is_available(self) -> bool:
        return self.client is not None

    def get_all_tool_definitions(self) -> list[dict]:
        return self.tool_definitions + self.MEMORY_TOOL_DEFINITIONS

    async def execute_tool(self, name: str, args: dict) -> Any:
        """Override in subclass to dispatch domain-specific tools."""
        raise NotImplementedError

    async def _dispatch_tool(self, name: str, args: dict) -> str:
        try:
            if name == "recall_memory":
                result = self.memory.recall(args["user_id"])
            elif name == "save_preference":
                self.memory.save_preference(args["user_id"], args["key"], args["value"])
                result = {"status": "saved", "key": args["key"]}
            else:
                result = await self.execute_tool(name, args)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    async def run(
        self,
        user_message: str,
        discord_id: Optional[int] = None,
        context: Optional[str] = None,
    ) -> AgentResult:
        if not self.client:
            return AgentResult(
                answer="AI is not configured. Set OPENAI_API_KEY in your .env file.",
                agent_name=self.name,
            )

        system_content = self.system_prompt
        if discord_id is not None:
            mem = self.memory.recall(discord_id)
            if mem["recent_conversations"] or mem["preferences"]:
                memory_block = json.dumps(mem, default=str, ensure_ascii=False)
                system_content += (
                    f"\n\n[User memory for Discord user {discord_id}]:\n{memory_block}"
                )

        messages: list[dict] = [{"role": "system", "content": system_content}]
        user_content = f"{context}\n\n{user_message}" if context else user_message
        messages.append({"role": "user", "content": user_content})

        tools = self.get_all_tool_definitions()
        tool_calls_log: list[dict] = []

        for iteration in range(1, self.max_iterations + 1):
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    max_tokens=1500,
                )
            except Exception as e:
                logger.error("[%s] LLM call failed on iteration %d: %s", self.name, iteration, e)
                return AgentResult(
                    answer=f"AI error: {e}",
                    agent_name=self.name,
                    tool_calls_made=tool_calls_log,
                    iterations=iteration,
                )

            choice = resp.choices[0]

            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                answer = choice.message.content or "I couldn't generate a response."
                if discord_id is not None:
                    self.memory.add_conversation(discord_id, user_message, answer)
                return AgentResult(
                    answer=answer,
                    agent_name=self.name,
                    tool_calls_made=tool_calls_log,
                    iterations=iteration,
                )

            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("[%s] Tool call [%d]: %s(%s)", self.name, iteration, fn_name, fn_args)
                result = await self._dispatch_tool(fn_name, fn_args)

                tool_calls_log.append({
                    "tool": fn_name,
                    "args": fn_args,
                    "iteration": iteration,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return AgentResult(
            answer="I ran out of steps trying to answer. Please try a simpler question.",
            agent_name=self.name,
            tool_calls_made=tool_calls_log,
            iterations=self.max_iterations,
        )
