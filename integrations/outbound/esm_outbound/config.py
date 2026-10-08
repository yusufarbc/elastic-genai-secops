"""Build adapters from environment variables. An adapter is enabled when its URL/key is set.

Notifications (sent for new cases at or above NOTIFY_MIN_SEVERITY):
  SLACK_WEBHOOK_URL, TEAMS_WEBHOOK_URL, WEBHOOK_URL (+ WEBHOOK_TOKEN),
  SMTP_HOST, SMTP_PORT (587), SMTP_FROM, SMTP_TO (comma separated), SMTP_USER, SMTP_PASSWORD,
  SMTP_STARTTLS (true)
Ticketing (created when an analyst approves a case, see TICKET_ON):
  THEHIVE_URL, THEHIVE_API_KEY
  JIRA_URL, JIRA_USER, JIRA_API_TOKEN, JIRA_PROJECT, JIRA_ISSUE_TYPE (Task)
Threat intel (used by enrichment-service):
  ABUSEIPDB_API_KEY, ABUSEIPDB_MIN_SCORE (50), MISP_URL, MISP_API_KEY, MISP_VERIFY_TLS (true)
"""

from __future__ import annotations

import os

import httpx

from esm_outbound.notifiers import (
    EmailNotifier,
    Notifier,
    SlackNotifier,
    TeamsNotifier,
    WebhookNotifier,
)
from esm_outbound.threatintel import MISP, AbuseIPDB, ThreatIntel, ThreatIntelSource
from esm_outbound.ticketing import JiraSink, TheHiveSink, TicketSink


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def notifiers_from_env(client: httpx.AsyncClient) -> list[Notifier]:
    out: list[Notifier] = []
    if url := _env("SLACK_WEBHOOK_URL"):
        out.append(SlackNotifier(url, client))
    if url := _env("TEAMS_WEBHOOK_URL"):
        out.append(TeamsNotifier(url, client))
    if url := _env("WEBHOOK_URL"):
        out.append(WebhookNotifier(url, client, _env("WEBHOOK_TOKEN")))
    if host := _env("SMTP_HOST"):
        recipients = [r.strip() for r in _env("SMTP_TO").split(",") if r.strip()]
        if not recipients:
            raise ValueError("SMTP_HOST is set but SMTP_TO is empty")
        out.append(EmailNotifier(host, int(_env("SMTP_PORT", "587")), _env("SMTP_FROM"),
                                 recipients, _env("SMTP_USER"), _env("SMTP_PASSWORD"),
                                 _env("SMTP_STARTTLS", "true").lower() == "true"))
    return out


def ticket_sinks_from_env(client: httpx.AsyncClient) -> list[TicketSink]:
    out: list[TicketSink] = []
    if url := _env("THEHIVE_URL"):
        out.append(TheHiveSink(url, _env("THEHIVE_API_KEY"), client))
    if url := _env("JIRA_URL"):
        out.append(JiraSink(url, _env("JIRA_USER"), _env("JIRA_API_TOKEN"), _env("JIRA_PROJECT"),
                            client, _env("JIRA_ISSUE_TYPE", "Task")))
    return out


def threat_intel_from_env() -> ThreatIntel:
    sources: list[ThreatIntelSource] = []
    if key := _env("ABUSEIPDB_API_KEY"):
        sources.append(AbuseIPDB(key, httpx.AsyncClient(timeout=10),
                                 int(_env("ABUSEIPDB_MIN_SCORE", "50"))))
    if url := _env("MISP_URL"):
        verify = _env("MISP_VERIFY_TLS", "true").lower() == "true"
        sources.append(MISP(url, _env("MISP_API_KEY"), httpx.AsyncClient(timeout=10,
                                                                           verify=verify)))
    return ThreatIntel(sources)
