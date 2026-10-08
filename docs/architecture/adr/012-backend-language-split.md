# ADR-012: Backend language split: Go for operational services, Python for AI/enrichment services

**Status:** Accepted · **Date:** 2026-06-30

**Context:** The language split must be justified in an ADR. Services divide into two groups: (a) high-throughput, long-running daemons where binary size, startup latency, and resource footprint matter (`detection-service`, `alert-gateway`, `case-service`, `response-service`, `bff`); (b) AI/ML pipeline services where the Python ecosystem (Pydantic, LangChain-style async, Vertex AI SDK, spaCy for NER/masking) gives a productivity advantage (`enrichment-service`, `masking-service`, `llm-orchestrator`).

**Alternatives considered:**

- All Go — would require reimplementing ecosystem tooling for AI/NLP; available Vertex AI SDK for Go is less mature than Python.
- All Python — GIL limits true parallelism for the stateless fan-out services; larger container images; slower cold-start for HPA scale-from-zero.
- Go for operational + Python for AI/enrichment — **chosen.**

**Rationale:** Go's static binaries, goroutine scheduler, and single-binary deploys make it ideal for `alert-gateway` (high-alert fanout) and `case-service` (concurrent case updates). Python's AI ecosystem (Vertex AI SDK, pydantic, asyncio) gives a faster iteration cycle on the enrichment and LLM pipeline. Service boundaries are defined by explicit message schemas on Pub/Sub, so each language is isolated behind its contract — no cross-language RPC in the hot path.

**Risks / follow-ups:** Two language toolchains in CI; mitigated by keeping Go tooling (golangci-lint, go test) and Python tooling (ruff, pytest, mypy) in separate CI job groups that mirror each other structurally.
