"""Notification channels: Slack, Microsoft Teams, generic webhook, e-mail (SMTP)."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx
from esm_common.contracts import CaseEvent

from esm_outbound.render import Message


class Notifier(Protocol):
    name: str

    async def send(self, message: Message, event: CaseEvent) -> None: ...


class SlackNotifier:
    """Slack incoming webhook."""

    name = "slack"

    def __init__(self, webhook_url: str, client: httpx.AsyncClient) -> None:
        self._url, self._client = webhook_url, client

    async def send(self, message: Message, event: CaseEvent) -> None:
        text = message.markdown().replace("**", "*")  # Slack mrkdwn uses single asterisks
        text = text.replace(f"[Open case]({message.link})", f"<{message.link}|Open case>")
        resp = await self._client.post(self._url, json={"text": text})
        resp.raise_for_status()


class TeamsNotifier:
    """Microsoft Teams workflow webhook (Adaptive Card)."""

    name = "teams"

    def __init__(self, webhook_url: str, client: httpx.AsyncClient) -> None:
        self._url, self._client = webhook_url, client

    async def send(self, message: Message, event: CaseEvent) -> None:
        body: list[dict] = [
            {"type": "TextBlock", "text": message.title, "weight": "Bolder", "wrap": True},
            {"type": "FactSet", "facts": [{"title": k, "value": v} for k, v in message.facts]},
        ]
        for heading, items in message.sections:
            body.append({"type": "TextBlock", "text": heading, "weight": "Bolder", "wrap": True})
            body.append({"type": "TextBlock", "text": "\n".join(f"- {i}" for i in items),
                         "wrap": True})
        card = {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard", "version": "1.4", "body": body}
        if message.link:
            card["actions"] = [
                {"type": "Action.OpenUrl", "title": "Open case", "url": message.link}
            ]
        resp = await self._client.post(self._url, json={
            "type": "message",
            "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive",
                             "content": card}],
        })
        resp.raise_for_status()


class WebhookNotifier:
    """Generic JSON webhook (SOAR, chat bots, custom receivers)."""

    name = "webhook"

    def __init__(self, url: str, client: httpx.AsyncClient, token: str = "") -> None:
        self._url, self._client = url, client
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def send(self, message: Message, event: CaseEvent) -> None:
        resp = await self._client.post(self._url, headers=self._headers, json={
            "event": event.event,
            "case_id": event.case_id,
            "title": message.title,
            "facts": dict(message.facts),
            "sections": {h: items for h, items in message.sections},
            "link": message.link,
        })
        resp.raise_for_status()


class EmailNotifier:
    """SMTP e-mail (STARTTLS by default)."""

    name = "email"

    def __init__(self, host: str, port: int, sender: str, recipients: list[str],
                 username: str = "", password: str = "", starttls: bool = True) -> None:
        self._host, self._port, self._sender, self._to = host, port, sender, recipients
        self._user, self._password, self._starttls = username, password, starttls

    def _send_sync(self, message: Message) -> None:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = message.title, self._sender, ", ".join(self._to)
        msg.set_content(message.plain())
        with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
            if self._starttls:
                smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(msg)

    async def send(self, message: Message, event: CaseEvent) -> None:
        await asyncio.to_thread(self._send_sync, message)
