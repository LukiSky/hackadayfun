"""Dashboard chat message handler (POST /api/chat/message contract)."""

from __future__ import annotations

from agents.dashboard_insights import generate_dashboard_insight

_CHART_WIDGET_IDS = {
    "outcome by region": "chart-region",
    "average outcome score by region": "chart-region",
    "sentiment score trend over time": "chart-sentiment",
    "sentiment trend": "chart-sentiment",
    "outcome by workshop": "chart-workshop",
    "average outcome score by workshop": "chart-workshop",
    "feedback by theme": "chart-theme",
    "outcome by workshop topic": "chart-theme",
}


def _commands_from_filters(active_filters: dict) -> list[dict]:
    commands: list[dict] = []
    for field, value in (active_filters or {}).items():
        if value and value != "All":
            commands.append(
                {
                    "action": "filter-table",
                    "targetWidgetId": f"filter-{field}",
                    "value": {"field": field, "value": value},
                }
            )
    return commands


def _command_from_suggested_chart(suggested: str | None) -> dict | None:
    if not suggested:
        return None
    widget_id = _CHART_WIDGET_IDS.get(suggested.strip().lower())
    if not widget_id:
        widget_id = "chart-region"
    return {
        "action": "focus-widget",
        "targetWidgetId": widget_id,
        "value": {"chart": suggested},
    }


def build_dashboard_commands(
    *,
    active_filters: dict,
    suggested_chart: str | None,
    pending: list[dict] | None = None,
) -> list[dict]:
    """Merge filter commands, chart focus, and client-proposed commands."""
    seen: set[str] = set()
    merged: list[dict] = []

    def add(cmd: dict) -> None:
        key = f"{cmd.get('action')}:{cmd.get('targetWidgetId')}:{cmd.get('value')}"
        if key in seen:
            return
        seen.add(key)
        merged.append(cmd)

    for cmd in pending or []:
        if isinstance(cmd, dict) and cmd.get("action"):
            add(cmd)

    for cmd in _commands_from_filters(active_filters):
        add(cmd)

    chart_cmd = _command_from_suggested_chart(suggested_chart)
    if chart_cmd:
        add(chart_cmd)

    return merged


def handle_chat_message(payload: dict) -> dict:
    """
    Spec response: { botReply, dashboardCommands, source?, errorMessage? }.
    """
    text = (payload.get("text") or "").strip()
    active_filters = payload.get("activeFilters") or {}
    pending = payload.get("pendingDashboardCommands") or []

    insight_payload = {
        "question": text,
        "mode": "chat",
        "activeFilters": active_filters,
        "aggregates": payload.get("aggregates") or {},
        "evidenceRows": payload.get("evidenceRows") or [],
        "availableFields": payload.get("availableFields") or {},
    }
    insight = generate_dashboard_insight(insight_payload)

    commands = build_dashboard_commands(
        active_filters=active_filters,
        suggested_chart=insight.get("suggestedChart"),
        pending=pending,
    )

    result = {
        "botReply": insight.get("answer") or "",
        "dashboardCommands": commands,
        "source": insight.get("source", "local"),
    }
    if insight.get("errorMessage"):
        result["errorMessage"] = insight["errorMessage"]
    if insight.get("summaryBullets"):
        result["summaryBullets"] = insight["summaryBullets"]
    if insight.get("evidenceReferences"):
        result["evidenceReferences"] = insight["evidenceReferences"]
    if insight.get("linkedDataPoints"):
        result["linkedDataPoints"] = insight["linkedDataPoints"]
    return result
