"""Tool definitions and executor for the ReAct agent."""

import json
from dataclasses import asdict
from typing import Any, Optional

from services.leetcode import LeetCodeService, LeetCodeAPIError


TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_challenge",
            "description": "Get today's LeetCode daily coding challenge, including the problem title, link, and difficulty.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_problem",
            "description": "Look up a specific LeetCode problem by its numeric ID (e.g. 1) or slug (e.g. 'two-sum'). Returns full problem details including description, difficulty, topics, and acceptance rate.",
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
            "description": "Search LeetCode problems by a text query string. Returns a list of matching problems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'binary search' or 'knapsack'",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_problems_by_tag",
            "description": "Get LeetCode problems filtered by topic tag (e.g. 'dynamic-programming', 'two-pointers', 'array', 'tree', 'graph'). Optionally filter by difficulty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "LeetCode topic tag slug, e.g. 'dynamic-programming', 'binary-search', 'tree'",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["Easy", "Medium", "Hard"],
                        "description": "Filter by difficulty level",
                    },
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
                    "difficulty": {
                        "type": "string",
                        "enum": ["Easy", "Medium", "Hard"],
                        "description": "Filter by difficulty level",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Filter by topic tag slug, e.g. 'array', 'tree'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_stats",
            "description": "Get a LeetCode user's profile and solve statistics: total solved, easy/medium/hard breakdown, ranking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "LeetCode username",
                    },
                },
                "required": ["username"],
            },
        },
    },
]

NOTIFY_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_notify_status",
            "description": "Check whether daily LeetCode challenge notifications are enabled for the current Discord server, and if so, which channel and time they are configured for.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guild_id": {
                        "type": "integer",
                        "description": "The Discord server (guild) ID",
                    },
                },
                "required": ["guild_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_notify",
            "description": "Enable daily LeetCode challenge notifications for a Discord server. Posts the daily problem to the specified channel at the given UTC time each day.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guild_id": {
                        "type": "integer",
                        "description": "The Discord server (guild) ID",
                    },
                    "channel_id": {
                        "type": "integer",
                        "description": "The channel ID to post daily challenges in",
                    },
                    "hour": {
                        "type": "integer",
                        "description": "Hour to send (0-23, UTC). Default: 8",
                    },
                    "minute": {
                        "type": "integer",
                        "description": "Minute to send (0-59, UTC). Default: 0",
                    },
                },
                "required": ["guild_id", "channel_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_notify",
            "description": "Disable daily LeetCode challenge notifications for a Discord server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guild_id": {
                        "type": "integer",
                        "description": "The Discord server (guild) ID",
                    },
                },
                "required": ["guild_id"],
            },
        },
    },
]


class ToolExecutor:
    """Dispatches tool calls to the appropriate service methods."""

    def __init__(self, leetcode: LeetCodeService, notify_cog: Optional[Any] = None):
        self.leetcode = leetcode
        self.notify_cog = notify_cog

    def get_tool_definitions(self) -> list[dict]:
        tools = list(TOOL_DEFINITIONS)
        if self.notify_cog is not None:
            tools.extend(NOTIFY_TOOL_DEFINITIONS)
        return tools

    async def execute(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool by name and return a JSON-serialized result string."""
        try:
            result = await self._dispatch(tool_name, arguments)
            return json.dumps(result, default=str, ensure_ascii=False)
        except LeetCodeAPIError as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    async def _dispatch(self, name: str, args: dict) -> Any:
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
            return self._format_problem_list(problems[:15])

        if name == "get_problems_by_tag":
            problems = await self.leetcode.get_problems_by_tag(
                args["tag"], limit=50
            )
            difficulty = args.get("difficulty")
            if difficulty:
                problems = [
                    p for p in problems if p.get("difficulty") == difficulty
                ]
            return self._format_problem_list(problems[:15])

        if name == "get_random_problem":
            prob = await self.leetcode.get_random_problem(
                difficulty=args.get("difficulty"),
                tag=args.get("tag"),
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

        if name == "get_notify_status" and self.notify_cog:
            cfg = self.notify_cog._guild_configs.get(args["guild_id"])
            if not cfg or not cfg.get("enabled"):
                return {"enabled": False}
            return {
                "enabled": True,
                "channel_id": cfg["channel_id"],
                "hour": cfg["hour"],
                "minute": cfg["minute"],
                "last_sent": cfg.get("last_sent"),
            }

        if name == "setup_notify" and self.notify_cog:
            import config as _cfg
            h = args.get("hour", _cfg.DAILY_NOTIFY_HOUR)
            m = args.get("minute", _cfg.DAILY_NOTIFY_MINUTE)
            self.notify_cog._guild_configs[args["guild_id"]] = {
                "channel_id": args["channel_id"],
                "hour": h,
                "minute": m,
                "enabled": True,
                "last_sent": None,
            }
            self.notify_cog._save_config()
            return {"status": "enabled", "channel_id": args["channel_id"], "hour": h, "minute": m}

        if name == "stop_notify" and self.notify_cog:
            cfg = self.notify_cog._guild_configs.get(args["guild_id"])
            if not cfg or not cfg.get("enabled"):
                return {"status": "already_disabled"}
            cfg["enabled"] = False
            self.notify_cog._save_config()
            return {"status": "disabled"}

        return {"error": f"Unknown tool: {name}"}

    @staticmethod
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
