from __future__ import annotations

import re
from typing import Any, Iterable


EVENT_TYPE_ACHIEVEMENT = "achievement"
EVENT_TYPE_GAME_START = "game_start"
FORWARD_MODE_AUTO = "auto"
FORWARD_MODE_FORWARD = "forward"
FORWARD_MODE_PLAIN = "plain"
AIOCQHTTP_SESSION_PREFIX = "aiocqhttp:"
ACHIEVEMENT_SUFFIX_RE = re.compile(r"[，,]\s*并?解锁了\s*\d+\s*个新成就$")


def build_notification_event(
    *,
    event_type: str,
    group_id: str,
    steamid: str,
    player_name: str,
    gameid: str,
    game_name: str,
    summary_text: str,
    image_path: str | None = None,
    achievement_names: Iterable[str] | None = None,
    achievement_total: int | None = None,
    occurred_at: int | float | None = None,
) -> dict[str, Any]:
    return {
        "type": event_type,
        "group_id": str(group_id),
        "steamid": str(steamid),
        "player_name": player_name,
        "gameid": str(gameid),
        "game_name": game_name,
        "summary_text": summary_text,
        "image_path": image_path,
        "achievement_names": list(achievement_names or []),
        "achievement_total": achievement_total,
        "occurred_at": occurred_at,
    }


def fold_notification_events(
    events: Iterable[dict[str, Any]], merge_achievements: bool = True
) -> list[dict[str, Any]]:
    folded: list[dict[str, Any]] = []
    for raw_event in events:
        event = _copy_event(raw_event)
        if event["type"] != EVENT_TYPE_ACHIEVEMENT or not merge_achievements:
            if event["type"] == EVENT_TYPE_ACHIEVEMENT:
                event["summary_text"] = _build_achievement_summary(event)
            folded.append(event)
            continue

        merge_target = _find_merge_target(folded, event)
        if merge_target:
            _merge_achievement_event(merge_target, event)
            continue

        event["summary_text"] = _build_achievement_summary(event)
        folded.append(event)
    return folded


class NotificationBufferStore:
    def __init__(self, max_events: int) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be greater than zero")
        self._max_events = max_events
        self._buffers: dict[str, list[dict[str, Any]]] = {}

    @property
    def buffers(self) -> dict[str, list[dict[str, Any]]]:
        return self._buffers

    def enqueue(self, event: dict[str, Any]) -> dict[str, Any]:
        group_id = str(event["group_id"])
        bucket = self._buffers.setdefault(group_id, [])
        start_window = len(bucket) == 0
        bucket.append(_copy_event(event))
        buffer_size = len(bucket)
        return {
            "group_id": group_id,
            "start_window": start_window,
            "flush_now": buffer_size >= self._max_events,
            "buffer_size": buffer_size,
        }

    def pop_group(self, group_id: str) -> list[dict[str, Any]]:
        return self._buffers.pop(str(group_id), [])


def should_use_forward_delivery(mode: str, notify_session: str) -> bool:
    normalized_mode = (mode or "").strip().lower()
    if normalized_mode == FORWARD_MODE_FORWARD:
        return True
    if normalized_mode == FORWARD_MODE_PLAIN:
        return False
    return notify_session.startswith(AIOCQHTTP_SESSION_PREFIX)


def _copy_event(event: dict[str, Any]) -> dict[str, Any]:
    copied = dict(event)
    copied["achievement_names"] = list(copied.get("achievement_names") or [])
    copied["achievement_total"] = copied.get("achievement_total")
    return copied


def _can_merge_achievement(target: dict[str, Any], achievement: dict[str, Any]) -> bool:
    if target["type"] not in {EVENT_TYPE_ACHIEVEMENT, EVENT_TYPE_GAME_START}:
        return False
    return _merge_key(target) == _merge_key(achievement)


def _find_merge_target(
    folded: list[dict[str, Any]], achievement: dict[str, Any]
) -> dict[str, Any] | None:
    for target in reversed(folded):
        if _can_merge_achievement(target, achievement):
            return target
    return None


def _merge_key(event: dict[str, Any]) -> tuple[str, str, str]:
    return (str(event["group_id"]), str(event["steamid"]), str(event["gameid"]))


def _merge_achievement_event(
    target: dict[str, Any], achievement_event: dict[str, Any]
) -> None:
    target_total = _achievement_total(target)
    event_total = _achievement_total(achievement_event)
    target["achievement_names"] = [
        *target.get("achievement_names", []),
        *achievement_event.get("achievement_names", []),
    ]
    target["achievement_total"] = target_total + event_total
    latest_image_path = achievement_event.get("image_path")
    if latest_image_path:
        target["image_path"] = latest_image_path
    if achievement_event.get("occurred_at") is not None:
        target["occurred_at"] = achievement_event["occurred_at"]

    if target["type"] == EVENT_TYPE_GAME_START:
        target["summary_text"] = _build_game_start_with_achievement_summary(target)
        return
    target["summary_text"] = _build_achievement_summary(target)


def _build_achievement_summary(event: dict[str, Any]) -> str:
    count = _achievement_total(event)
    return (
        f"🏆【{event['player_name']}】在 {event['game_name']} 解锁了 {count} 个新成就"
    )


def _build_game_start_with_achievement_summary(event: dict[str, Any]) -> str:
    base_summary = event.get("summary_text") or ""
    base_summary = ACHIEVEMENT_SUFFIX_RE.sub("", base_summary)
    return f"{base_summary}，并解锁了 {_achievement_total(event)} 个新成就"


def _achievement_total(event: dict[str, Any]) -> int:
    total = event.get("achievement_total")
    if isinstance(total, int) and total > 0:
        return total
    return len(event.get("achievement_names", []))
