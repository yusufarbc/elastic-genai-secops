"""Ticketing: TheHive 5 alerts and Jira issues. Both are idempotent per case."""

from __future__ import annotations

from typing import Protocol

import httpx
from esm_common.contracts import CaseEvent

from esm_outbound.render import SEVERITY_ORDER, Message


class TicketSink(Protocol):
    name: str

    async def create(self, message: Message, event: CaseEvent) -> str:
        """Create the ticket (or find the existing one) and return its reference."""


class TheHiveSink:
    """TheHive 5: one alert per case, deduplicated by sourceRef = case ID."""

    name = "thehive"

    def __init__(self, url: str, api_key: str, client: httpx.AsyncClient) -> None:
        self._url = url.rstrip("/")
        self._client = client
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def create(self, message: Message, event: CaseEvent) -> str:
        c = event.case
        resp = await self._client.post(f"{self._url}/api/v1/alert", headers=self._headers, json={
            "type": "esm-case",
            "source": "Elastic GenAI SecOps",
            "sourceRef": c.id,
            "title": message.title,
            "description": message.markdown(),
            "severity": SEVERITY_ORDER.get(c.severity, 2),
            "tags": ["esm", *(c.mitre_techniques or [])],
        })
        if resp.status_code == 400 and "exist" in resp.text.lower():
            return f"thehive:{c.id} (already exists)"
        resp.raise_for_status()
        return f"thehive:{resp.json().get('_id', c.id)}"


class JiraSink:
    """Jira (Cloud or Data Center, REST API v2): one issue per case, labelled esm-<case id>."""

    name = "jira"

    def __init__(self, url: str, user: str, token: str, project: str, client: httpx.AsyncClient,
                 issue_type: str = "Task") -> None:
        self._url = url.rstrip("/")
        self._auth = (user, token)
        self._project, self._issue_type, self._client = project, issue_type, client

    async def create(self, message: Message, event: CaseEvent) -> str:
        label = f"esm-{event.case.id}"
        found = await self._client.get(f"{self._url}/rest/api/2/search", auth=self._auth,
                                       params={"jql": f'labels = "{label}"', "maxResults": 1,
                                               "fields": "key"})
        found.raise_for_status()
        issues = found.json().get("issues", [])
        if issues:
            return f"jira:{issues[0]['key']} (already exists)"
        resp = await self._client.post(f"{self._url}/rest/api/2/issue", auth=self._auth, json={
            "fields": {
                "project": {"key": self._project},
                "issuetype": {"name": self._issue_type},
                "summary": message.title[:250],
                "description": message.plain(),
                "labels": ["esm", label],
            }
        })
        resp.raise_for_status()
        return f"jira:{resp.json()['key']}"
