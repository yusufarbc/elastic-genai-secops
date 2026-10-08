# ADR-020: Apache-2.0 license for the consolidated repository

**Status:** Accepted · **Date:** 2026-10-07

**Context:** The three source projects used MIT (repository root), GPL-3.0 (Elastic-GenAI-SOC) and AGPL-3.0 (the AI-SOC platform). One repository needs one license, and all three projects have the same copyright holder.

**Alternatives considered:**

- AGPL-3.0: strongest copyleft for a network service, but discourages enterprise adoption.
- MIT: simple, but no explicit patent grant.
- Apache-2.0: **chosen.**

**Rationale:** Permissive, includes an explicit patent grant, and is common in the Elastic and Kubernetes ecosystems. Earlier copies remain available under their original licenses in the git history.

**Follow-ups:** `NOTICE` records the relicensing. Third-party binaries (Beats, Sysmon) are not redistributed; they are downloaded at install time.
