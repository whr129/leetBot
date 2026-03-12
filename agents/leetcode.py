"""LeetCode specialist agent with isolated tools and memory."""

from dataclasses import asdict
from typing import Any, Optional

from openai import AsyncOpenAI

from agents.base import BaseAgent
from services.leetcode import LeetCodeService, LeetCodeAPIError
from services.memory import AgentMemory

SYSTEM_PROMPT = """\
You are a helpful LeetCode study assistant in a Discord server.

You can look up problems, search by topic, fetch daily challenges, and check user stats \
using the tools provided. Always use tools to retrieve real data rather than guessing.

Guidelines:
- Be concise and educational. Discord messages have a 2000-char limit.
- When listing problems, include the title, difficulty, and URL.
- When explaining concepts, use clear examples and mention time/space complexity.
- If the user asks about a specific problem, fetch it first with get_problem.
- Format your response using Markdown (bold, bullet points, code blocks) for readability in Discord.
- If you have saved preferences for this user (e.g. their LeetCode username), use them.
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_challenge",
            "description": "Get today's LeetCode daily coding challenge.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_problem",
            "description": "Look up a specific LeetCode problem by its numeric ID or slug.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_or_slug": {
                        "type": "string",
                        "description": "Problem ID number or URL slug, e.g. '1' or 'two-sum'",
                    },
                },
                "required": ["id_or_slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_problems",
            "description": "Search LeetCode problems by a text query string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_problems_by_tag",
            "description": "Get LeetCode problems filtered by topic tag. Optionally filter by difficulty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Topic tag slug, e.g. 'dynamic-programming'"},
                    "difficulty": {"type": "string", "enum": ["Easy", "Medium", "Hard"]},
                },
                "required": ["tag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_random_problem",
            "description": "Get a random LeetCode problem. Optionally filter by difficulty and/or topic tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "difficulty": {"type": "string", "enum": ["Easy", "Medium", "Hard"]},
                    "tag": {"type": "string", "description": "Topic tag slug"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_stats",
            "description": "Get a LeetCode user's profile and solve statistics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "LeetCode username"},
                },
                "required": ["username"],
            },
        },
    },
]


class LeetCodeAgent(BaseAgent):
    name = "leetcode"
    system_prompt = SYSTEM_PROMPT
    tool_definitions = TOOL_DEFINITIONS

    def __init__(
        self,
        client: Optional[AsyncOpenAI],
        leetcode: LeetCodeService,
        model: str = "gpt-4o-mini",
        max_iterations: int = 8,
        memory_ttl_days: int = 7,
        memory_max_conversations: int = 50,
    ):
        memory = AgentMemory("leetcode", ttl_days=memory_ttl_days, max_conversations=memory_max_conversations)
        super().__init__(client=client, memory=memory, model=model, max_iterations=max_iterations)
        self.leetcode = leetcode

    async def execute_tool(self, name: str, args: dict) -> Any:
        if name == "get_daily_challenge":
            daily = await self.leetcode.get_daily()
            return {
                "date": daily.date,
                "link": daily.link,
                "title": daily.question.get("title", ""),
                "difficulty": daily.question.get("difficulty", ""),
                "slug": daily.question.get("titleSlug", ""),
            }

        if name == "get_problem":
            prob = await self.leetcode.get_problem(args["id_or_slug"])
            return {
                "id": prob.frontend_id,
                "title": prob.title,
                "url": prob.url,
                "difficulty": prob.difficulty,
                "content": (prob.content or "")[:3000],
                "topic_tags": [
                    t.get("name", t) if isinstance(t, dict) else t
                    for t in (prob.topic_tags or [])
                ],
                "ac_rate": prob.ac_rate,
            }

        if name == "search_problems":
            problems = await self.leetcode.search_problems(args["query"])
            return _format_problem_list(problems[:15])

        if name == "get_problems_by_tag":
            problems = await self.leetcode.get_problems_by_tag(args["tag"], limit=50)
            difficulty = args.get("difficulty")
            if difficulty:
                problems = [p for p in problems if p.get("difficulty") == difficulty]
            return _format_problem_list(problems[:15])

        if name == "get_random_problem":
            prob = await self.leetcode.get_random_problem(
                difficulty=args.get("difficulty"), tag=args.get("tag"),
            )
            return {
                "id": prob.frontend_id,
                "title": prob.title,
                "url": prob.url,
                "difficulty": prob.difficulty,
                "topic_tags": [
                    t.get("name", t) if isinstance(t, dict) else t
                    for t in (prob.topic_tags or [])
                ],
            }

        if name == "get_user_stats":
            profile = await self.leetcode.get_user_profile(args["username"])
            return asdict(profile)

        return {"error": f"Unknown tool: {name}"}


def _format_problem_list(problems: list[dict]) -> list[dict]:
    return [
        {
            "title": p.get("title", "Unknown"),
            "url": p.get("url", f"https://leetcode.com/problems/{p.get('title_slug', p.get('titleSlug', ''))}/"),
            "difficulty": p.get("difficulty", "?"),
            "id": p.get("frontend_id", p.get("questionFrontendId", "")),
        }
        for p in problems
    ]
