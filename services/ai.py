"""ReAct agent for LeetCode assistance using OpenAI tool-calling."""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from openai import AsyncOpenAI

from services.tools import ToolExecutor

logger = logging.getLogger("leetbot.agent")

SYSTEM_PROMPT = """\
You are a helpful LeetCode study assistant in a Discord server.

You can look up problems, search by topic, fetch daily challenges, check user stats, \
and check user stats using the tools provided. Always use tools to retrieve \
real data rather than guessing or fabricating problem details.

Guidelines:
- Be concise and educational. Discord messages have a 2000-char limit.
- When listing problems, include the title, difficulty, and URL.
- When explaining concepts, use clear examples and mention time/space complexity.
- If the user asks about a specific problem, fetch it first with get_problem.
- Format your response using Markdown (bold, bullet points, code blocks) for readability in Discord.
"""


@dataclass
class AgentResult:
    """Result from a ReAct agent run."""

    answer: str
    tool_calls_made: list[dict] = field(default_factory=list)
    iterations: int = 0


class ReActAgent:
    """ReAct agent that reasons and acts using OpenAI tool-calling."""

    def __init__(
        self,
        api_key: str,
        tool_executor: ToolExecutor,
        model: str = "gpt-4o-mini",
        max_iterations: int = 8,
    ):
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.executor = tool_executor
        self.model = model
        self.max_iterations = max_iterations

    def is_available(self) -> bool:
        return self.client is not None

    async def run(
        self,
        user_message: str,
        context: Optional[str] = None,
        discord_id: Optional[int] = None,
    ) -> AgentResult:
        """
        Execute the ReAct loop:
        1. Build messages (system + context + user)
        2. Call LLM with tool definitions
        3. If tool_calls → execute, append results, repeat
        4. If text only → return final answer
        5. Stop after max_iterations
        """
        if not self.client:
            return AgentResult(
                answer="AI is not configured. Set OPENAI_API_KEY in your .env file."
            )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        user_content = user_message
        if context:
            user_content = f"{context}\n\n{user_message}"
        messages.append({"role": "user", "content": user_content})

        tools = self.executor.get_tool_definitions()
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
                logger.error(f"LLM call failed on iteration {iteration}: {e}")
                return AgentResult(
                    answer=f"AI error: {e}",
                    tool_calls_made=tool_calls_log,
                    iterations=iteration,
                )

            choice = resp.choices[0]

            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                answer = choice.message.content or "I couldn't generate a response."
                return AgentResult(
                    answer=answer,
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

                logger.info(f"Tool call [{iteration}]: {fn_name}({fn_args})")
                result = await self.executor.execute(fn_name, fn_args)

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
            tool_calls_made=tool_calls_log,
            iterations=self.max_iterations,
        )
