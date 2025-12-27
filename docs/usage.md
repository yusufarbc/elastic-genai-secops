# Usage Guide

## GenAI Alert Analysis

The GenAI SOC integration automatically enriches security alerts.

1. **Dashboard**: Open Kibana and navigate to the Security Dashboard.
2. **Alerts**: Trigger a test alert (or wait for real traffic).
3. **Enrichment**: View the alert details. You should see AI-generated insights and remediation steps appended to the alert.

## Monitoring

- Check `server.py` logs for connectivity issues with the LLM provider.
- Ensure Elasticsearch is reachable from the GenAI service.
