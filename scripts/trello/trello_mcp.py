from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP

API_BASE = "https://api.trello.com/1"
CARD_FIELDS = "id,name,desc,closed,start,due,dueComplete,dateLastActivity,idBoard,idList,url,shortUrl"
LIST_FIELDS = "id,name,closed,pos,idBoard"
BOARD_FIELDS = "id,name,desc,closed,url,shortUrl"

mcp = FastMCP(
    name="trello",
    instructions=(
        "Use this server to read and update Trello boards, lists, cards, and comments. "
        "Authentication comes from TRELLO_API_KEY and TRELLO_TOKEN environment variables."
    ),
)


class TrelloConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise TrelloConfigError(
            f"Missing {name}. Set it in shell or in MCP server env config before using Trello tools."
        )
    return value


def _auth_params() -> dict[str, str]:
    return {
        "key": _require_env("TRELLO_API_KEY"),
        "token": _require_env("TRELLO_TOKEN"),
    }


def _normalize_datetime(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned or cleaned.lower() == "null":
        return None

    if cleaned.endswith("Z"):
        datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        return cleaned

    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_bool(value: bool | None) -> str | None:
    if value is None:
        return None
    return str(value).lower()


def _trello_request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    params = _auth_params()
    if query:
        for key, value in query.items():
            if value is not None:
                params[key] = value

    url = f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"

    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            if not payload:
                return {}
            return json.loads(payload)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw
        raise RuntimeError(f"Trello API error {exc.code} on {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Trello API: {exc.reason}") from exc


def _compact_board(board: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": board.get("id"),
        "name": board.get("name"),
        "desc": board.get("desc"),
        "closed": board.get("closed"),
        "url": board.get("url"),
        "short_url": board.get("shortUrl"),
    }


def _compact_list(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "closed": item.get("closed"),
        "position": item.get("pos"),
        "id_board": item.get("idBoard"),
    }


def _compact_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "url": card.get("url"),
        "short_url": card.get("shortUrl"),
        "desc": card.get("desc"),
        "closed": card.get("closed"),
        "start": card.get("start"),
        "due": card.get("due"),
        "due_complete": card.get("dueComplete"),
        "date_last_activity": card.get("dateLastActivity"),
        "id_board": card.get("idBoard"),
        "id_list": card.get("idList"),
        "labels": [
            {"id": label.get("id"), "name": label.get("name"), "color": label.get("color")}
            for label in card.get("labels", [])
        ],
        "members": [
            {"id": member.get("id"), "full_name": member.get("fullName"), "username": member.get("username")}
            for member in card.get("members", [])
        ],
    }


def _compact_action(action: dict[str, Any]) -> dict[str, Any]:
    data = action.get("data", {}) or {}
    member_creator = action.get("memberCreator", {}) or {}
    return {
        "id": action.get("id"),
        "type": action.get("type"),
        "date": action.get("date"),
        "text": data.get("text"),
        "member_creator": {
            "id": member_creator.get("id"),
            "full_name": member_creator.get("fullName"),
            "username": member_creator.get("username"),
        },
        "data": data,
    }


@mcp.tool(name="trello_whoami", description="Check Trello auth and show the current account.")
def trello_whoami() -> dict[str, Any]:
    member = _trello_request("GET", "/members/me", query={"fields": "id,fullName,username,url"})
    return {
        "id": member.get("id"),
        "full_name": member.get("fullName"),
        "username": member.get("username"),
        "url": member.get("url"),
    }


@mcp.tool(name="trello_list_boards", description="List boards available to the authenticated Trello account.")
def trello_list_boards() -> list[dict[str, Any]]:
    boards = _trello_request(
        "GET",
        "/members/me/boards",
        query={"fields": BOARD_FIELDS, "lists": "none"},
    )
    return [_compact_board(board) for board in boards]


@mcp.tool(name="trello_get_board", description="Get a Trello board by ID.")
def trello_get_board(board_id: str) -> dict[str, Any]:
    board = _trello_request("GET", f"/boards/{board_id}", query={"fields": BOARD_FIELDS})
    return _compact_board(board)


@mcp.tool(name="trello_list_lists", description="List lists for a Trello board.")
def trello_list_lists(board_id: str, include_closed: bool = False) -> list[dict[str, Any]]:
    lists = _trello_request(
        "GET",
        f"/boards/{board_id}/lists",
        query={"fields": LIST_FIELDS, "filter": "all" if include_closed else "open"},
    )
    return [_compact_list(item) for item in lists]


@mcp.tool(name="trello_get_list", description="Get a Trello list by ID.")
def trello_get_list(list_id: str) -> dict[str, Any]:
    item = _trello_request("GET", f"/lists/{list_id}", query={"fields": LIST_FIELDS})
    return _compact_list(item)


@mcp.tool(name="trello_create_list", description="Create a new list on a Trello board.")
def trello_create_list(board_id: str, name: str, position: str = "bottom") -> dict[str, Any]:
    item = _trello_request(
        "POST",
        "/lists",
        query={"idBoard": board_id, "name": name, "pos": position},
    )
    return _compact_list(item)


@mcp.tool(name="trello_update_list", description="Update a Trello list.")
def trello_update_list(
    list_id: str,
    name: str | None = None,
    closed: bool | None = None,
    position: str | None = None,
) -> dict[str, Any]:
    query = {
        "name": name,
        "closed": _coerce_bool(closed),
        "pos": position,
    }
    query = {key: value for key, value in query.items() if value is not None}
    if not query:
        raise ValueError("Provide at least one field to update.")

    item = _trello_request("PUT", f"/lists/{list_id}", query=query)
    return _compact_list(item)


@mcp.tool(name="trello_list_cards", description="List cards in a Trello list.")
def trello_list_cards(list_id: str, include_closed: bool = False) -> list[dict[str, Any]]:
    cards = _trello_request(
        "GET",
        f"/lists/{list_id}/cards",
        query={
            "fields": CARD_FIELDS,
            "members": "true",
            "member_fields": "fullName,username",
            "labels": "true",
            "filter": "all" if include_closed else "open",
        },
    )
    return [_compact_card(card) for card in cards]


@mcp.tool(name="trello_search_cards", description="Search Trello cards by text, optionally within a board.")
def trello_search_cards(
    query: str,
    board_id: str | None = None,
    include_closed: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    search_query = query if not board_id else f"{query} board:{board_id}"
    cards = _trello_request(
        "GET",
        "/search",
        query={
            "query": search_query,
            "modelTypes": "cards",
            "card_fields": CARD_FIELDS,
            "cards_limit": max(1, min(limit, 100)),
            "card_members": "true",
            "card_member_fields": "fullName,username",
            "card_board": "true",
            "card_list": "true",
            "cards_page": 0,
            "partial": "true",
        },
    ).get("cards", [])

    if not include_closed:
        cards = [card for card in cards if not card.get("closed")]

    return [_compact_card(card) for card in cards]


@mcp.tool(name="trello_get_card", description="Get a Trello card by ID.")
def trello_get_card(card_id: str) -> dict[str, Any]:
    card = _trello_request(
        "GET",
        f"/cards/{card_id}",
        query={
            "fields": CARD_FIELDS,
            "members": "true",
            "member_fields": "fullName,username",
            "labels": "true",
        },
    )
    return _compact_card(card)


@mcp.tool(name="trello_create_card", description="Create a new Trello card in a list.")
def trello_create_card(
    list_id: str,
    name: str,
    description: str = "",
    start: str | None = None,
    due: str | None = None,
    position: str = "top",
) -> dict[str, Any]:
    card = _trello_request(
        "POST",
        "/cards",
        query={
            "idList": list_id,
            "name": name,
            "desc": description,
            "start": _normalize_datetime(start),
            "due": _normalize_datetime(due),
            "pos": position,
        },
    )
    return _compact_card(card)


@mcp.tool(name="trello_update_card", description="Update fields on an existing Trello card.")
def trello_update_card(
    card_id: str,
    name: str | None = None,
    description: str | None = None,
    list_id: str | None = None,
    start: str | None = None,
    due: str | None = None,
    due_complete: bool | None = None,
    closed: bool | None = None,
    position: str | None = None,
) -> dict[str, Any]:
    query = {
        "name": name,
        "desc": description,
        "idList": list_id,
        "start": _normalize_datetime(start) if start is not None else None,
        "due": _normalize_datetime(due) if due is not None else None,
        "dueComplete": _coerce_bool(due_complete),
        "closed": _coerce_bool(closed),
        "pos": position,
    }
    query = {key: value for key, value in query.items() if value is not None}
    if not query:
        raise ValueError("Provide at least one field to update.")

    card = _trello_request("PUT", f"/cards/{card_id}", query=query)
    return _compact_card(card)


@mcp.tool(name="trello_list_card_comments", description="List recent comments on a Trello card.")
def trello_list_card_comments(card_id: str, limit: int = 20) -> list[dict[str, Any]]:
    actions = _trello_request(
        "GET",
        f"/cards/{card_id}/actions",
        query={
            "filter": "commentCard",
            "limit": max(1, min(limit, 100)),
            "fields": "date,type,data,idMemberCreator",
            "memberCreator": "true",
            "memberCreator_fields": "fullName,username",
        },
    )
    return [_compact_action(action) for action in actions]


@mcp.tool(name="trello_add_card_comment", description="Add a comment to a Trello card.")
def trello_add_card_comment(card_id: str, text: str) -> dict[str, Any]:
    action = _trello_request(
        "POST",
        f"/cards/{card_id}/actions/comments",
        query={"text": text},
    )
    return _compact_action(action)


@mcp.tool(name="trello_get_card_activity", description="Get recent activity entries for a Trello card.")
def trello_get_card_activity(card_id: str, limit: int = 20, filter: str = "all") -> list[dict[str, Any]]:
    actions = _trello_request(
        "GET",
        f"/cards/{card_id}/actions",
        query={
            "filter": filter,
            "limit": max(1, min(limit, 100)),
            "fields": "date,type,data,idMemberCreator",
            "memberCreator": "true",
            "memberCreator_fields": "fullName,username",
        },
    )
    return [_compact_action(action) for action in actions]


if __name__ == "__main__":
    mcp.run()
