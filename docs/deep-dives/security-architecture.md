[← Back to README](../../README.md)

# Elastic Security: From SIEM to XDR

## 1. Elastic Common Schema (ECS)
The foundation of Elastic Security is the **Elastic Common Schema (ECS)**.
*   **Field Hierarchy**: Enforces strict naming (e.g., `source.ip`, `event.action`).
*   **Standardization**: Defines strict data types (e.g., `ip` type for CIDR queries).
*   **Reusability**: Allows detection rules to be source-agnostic. A rule for `process.name: "mimikatz.exe"` works seamlessly across Winlogbeat, Sysmon, or Elastic Endpoint.

## 2. The Endpoint and "Reflex" Engine
The acquisition of Endgame provided the **Elastic Endpoint**, a kernel-level agent.
*   **Architecture**: Runs as a privileged service (System/Root). Uses kernel callbacks (ETW, eBPF/Auditd).
*   **Reflex Engine**: An internal decision engine that evaluates events locally against prevention policies (malware signatures, behavioral heuristics).
*   **Autonomous Response**: Can block execution or terminate processes in sub-millisecond timeframes *without* network connectivity to the stack.

## 3. Event Query Language (EQL)
To support threat hunting, Elastic integrated **EQL**, designed for expressing relationships between events over time.

### 3.1 Sequences
EQL enables sequence queries:
```eql
sequence by host.id with maxspan=1m
  [process where event.type == "start" and process.name == "cmd.exe"]
  [network where destination.port == 443]
```
This finds a `cmd.exe` execution followed by a network connection on port 443 on the same host within 1 minute.

### 3.2 Execution Model
EQL queries are executed directly on the data nodes.
1.  Coordination node distributes query.
2.  Data nodes identify candidate events using Lucene.
3.  Data nodes perform stateful correlation (joining by `join_keys` like `process.entity_id`) locally.
4.  Results allow performant correlation across massive datasets without excessive data transfer.
