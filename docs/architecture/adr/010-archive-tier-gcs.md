# ADR-010: Archive tier: GCS object storage (NOT Google Drive)

**Status:** Accepted · **Date:** 2026-06-30

**Context:** After 14 days of hot data, older data is archived elsewhere. Google Drive was suggested as the archive target.

**Alternatives considered:**
- Google Drive — rejected: Drive is a file-sharing service, not object storage. Elasticsearch snapshot repositories require S3-compatible / GCS blob storage. There is no "snapshot to Drive" path; Drive also has quota/file-count limits and no storage-class tiering.
- GCS (Google Cloud Storage) — **chosen.**

**Rationale:** Already on GCP. Elasticsearch has an official GCS snapshot repository plugin. GCS storage classes (Standard → Nearline → Coldline → Archive) auto-reduce cost as data ages via a lifecycle policy — ideal for rarely-accessed SOC log archives.

**Two archive concepts distinguished:**
1. **Snapshot archive (disaster recovery):** full index/cluster backups to GCS. Always required.
2. **Searchable archive (still queryable old data):** Elasticsearch "searchable snapshots" — **verify license tier**; may be a paid feature, may not be in Basic/open-source. Do not depend on it until confirmed.

**Chosen default flow:** ILM snapshots the index to GCS at 14 days, deletes it from hot tier; raw snapshot sits in GCS (Archive class) for infrequent restore (audit/forensics). If frequent fast search over old data is later required, revisit searchable snapshots (license + cost question).

**ILM flow:**
```
New log → Hot tier (Elasticsearch, GKE disk)   [0–14 days]  fast, active triage
   ↓ at 14 days
Snapshot → GCS bucket                          [archive]    object storage, not Drive
   ↓
Delete index from hot tier                                  free the disk
   ↓ GCS lifecycle policy
GCS: Standard → Nearline → Coldline → Archive  [as it ages] cost drops
```

**Risks / follow-ups:** Legal/regulatory retention period (KVKK, sector rules) is a SEPARATE decision from the 14-day operational hot window — security logs may carry a longer mandated retention. Set GCS retention to the regulatory requirement; do not conflate it with the hot window.
