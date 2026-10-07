[← Back to README](../../README.md)

# Ingestion Architecture: Logstash and Beats

## 1. Logstash: The JRuby Processing Engine
Logstash is the heavy-lifting ETL (Extract, Transform, Load) tool of the stack, running on **JRuby** to leverage the vast ecosystem of Java libraries while maintaining Ruby's flexibility for configuration.

### 1.1 Persistent Queues (PQ): Architecture and Crash Recovery
Originally, Logstash relied on an in-memory queue (risk of data loss). The **Persistent Queue (PQ)** introduced on-disk durability.
*   **Page Files**: The queue represents a sequence of fixed-size "page files" (default 64MB or 250MB).
*   **Head Page**: Active file receiving new write operations (append-only log).
*   **Tail Pages**: Immutable, read-only pages rotated from Head.
*   **Checkpointing**: Tracks processing state. Updated after every $N$ writes.
*   **ACknowledgements**: As pipeline outputs events, it sends ACKs. The checkpoint records the offset.
*   **Reclamation**: Page files are deleted only when *every* event in the page is ACKed.

## 2. Beats: Lightweight Shippers and Libbeat
Beats are single-purpose data shippers written in **Go**, sharing a common library called `libbeat`.

### 2.1 The Memory Queue: Ring Buffer vs. Channels
`libbeat` implements its internal memory queue using a **Ring Buffer** protected by a mutex, rather than Go Channels (`chan`).
*   **Rationale**: Benchmarks showed that under high throughput, Go channels introduced significant contention and garbage collection overhead.
*   **Implementation**: A fixed-size circular array. Publisher/consumer grab mutex, batch operation, release. This proved more performant and predictable for log shipping patterns.

### 2.2 The Lumberjack Protocol (V2)
Beats communicate with Logstash using the **Lumberjack protocol (version 2)**, a binary protocol designed for reliability and backpressure.

**Frame Structure**
*   **Magic Byte**: e.g., `0x32` for v2.
*   **Sequence Numbers**: Included in every frame.
*   **Window Size and Backpressure**:
    1.  Beat sends a window of events (e.g., 1024 frames).
    2.  Beat pauses until it receives an ACK.
    3.  Logstash sends ACK only after processing.
    4.  **Backpressure Propagation**: If Elasticsearch slows down, Logstash delays ACKs. Beat's window fills, internal Ring Buffer fills, and eventually, the input (file reader) is paused. This prevents memory overflows.
