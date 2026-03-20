NETWORK_FLAP_WINDOW_SEC = 180


async def handle_recent_reconnect(
    *,
    group_id,
    sid,
    current_gameid,
    now,
    quit_info,
    pending_quit_tasks,
    pending_quit,
    last_states,
    status,
):
    if not _is_recent_reconnect(quit_info, now):
        return False

    _cancel_pending_quit_task(pending_quit_tasks, group_id, sid, current_gameid)
    _clear_pending_quit_entry(pending_quit, sid, current_gameid)
    quit_info["notified"] = True
    last_states[sid] = status
    return True


def _is_recent_reconnect(quit_info, now):
    if not quit_info:
        return False
    if quit_info.get("notified"):
        return False
    quit_time = quit_info.get("quit_time")
    if quit_time is None:
        return False
    return now - quit_time <= NETWORK_FLAP_WINDOW_SEC


def _cancel_pending_quit_task(pending_quit_tasks, group_id, sid, current_gameid):
    group_tasks = pending_quit_tasks.get(group_id, {})
    sid_tasks = group_tasks.get(sid, {})
    task = sid_tasks.get(current_gameid)
    if not task:
        return
    task.cancel()
    sid_tasks.pop(current_gameid, None)


def _clear_pending_quit_entry(pending_quit, sid, current_gameid):
    sid_pending = pending_quit.get(sid, {})
    sid_pending.pop(current_gameid, None)
