# Project Context & Evolution

## 1. Genesis and Evolution
*From "The Pre-Cambrian Era" to Active Defense*

The Elastic Stack began in 2004 with **Compass**, a search mapping framework by Shay Banon. It evolved into **Elasticsearch** (2010), designed to be distributed by default. The ecosystem grew with **Logstash** (ingestion) and **Kibana** (visualization), forming the ELK Stack.

### The Security Pivot
The acquisition of **Endgame** (2019) marked the transition from passive SIEM to active XDR.
*   **Elastic Endpoint**: A kernel-level agent for malware prevention.
*   **Reflex Engine**: Local decision-making without cloud connectivity.
*   **EQL**: Event Query Language for complex threat hunting.

## 2. Technical Architecture & Data Structures

### Primary Data Structures
| Component | Structure | Optimization |
| :--- | :--- | :--- |
| **Search** | Inverted Index (Segments) | **Frame of Reference (FOR)**: Delta-encoding + Bit-packing. |
| **Caching** | Roaring Bitmaps | **Hybrid Encoding**: Sparse arrays vs. Dense bitmaps. |
| **Geo/Numeric** | BKD Tree | **Block-Packing**: Efficient N-dimensional range queries. |
| **Queues** | Ring Buffer (Beats) | **Mutex-Guarded**: Avoids Go Channel GC pressure. |

### Protocols
*   **Lumberjack V2** (Logstash/Beats): Uses a "Window Size" mechanism for backpressure. If Elasticsearch slows down, Logstash stops sending ACKs, forcing Beats to pause reading inputs.

## 3. Comparative Analysis
The Elastic Stack's architecture differs significantly from traditional databases by prioritizing:
1.  **Immutability**: Segments are never modified, allowing aggressive OS page caching.
2.  **Schema-on-Write**: Data is mapped and indexed at ingestion time, unlike Schema-on-Read (Splunk).
3.  **Eventual Consistency**: Emphasizes availability and partition tolerance (AP) over strict consistency (CP) for search operations.
