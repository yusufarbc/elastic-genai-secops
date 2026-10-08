[← Back to README](../../README.md)

# Elasticsearch Core Internals & Architecture

## 1. Lucene Internals: The Atomic Unit of Search
Elasticsearch is, at its core, a sophisticated distributed system wrapper around Apache Lucene. To understand the performance characteristics of the stack, one must understand the data structures and algorithms of Lucene.

### 1.1 The Inverted Index and Immutable Segments
The fundamental data structure of Lucene is the **inverted index**. Unlike a forward index (which maps documents to terms), the inverted index maps terms to the documents containing them. This structure is analogous to the index at the back of a book and allows for $O(1)$ or $O(\log n)$ lookup complexity for term queries.

Lucene indices are composed of **segments**. A segment is a self-contained, immutable inverted index. When a new document is added, it is not inserted into an existing structure; rather, it is written to a new segment. This immutability is crucial for concurrency and performance:
*   **No Locking**: Since segments are never modified, multiple threads can read from them without expensive locking mechanisms.
*   **Caching Efficiency**: The operating system's kernel page cache can aggressively cache these files. Since the bits on disk never change, the cache remains valid until the segment is merged or deleted, maximizing the utility of available RAM.

### 1.2 Compression Algorithms
The inverted index consists of two primary components: the Terms Dictionary (the vocabulary) and the Postings List (the list of document IDs for each term).

**Frame of Reference (FOR)**
Lucene utilizes Frame of Reference (FOR) compression for on-disk storage of postings lists.
*   **Delta Encoding**: Instead of storing raw document IDs (e.g., 100, 105, 108), Lucene stores the differences (deltas) between them (e.g., 100, 5, 3).
*   **Bit Packing**: The deltas are grouped into blocks (typically 256 integers). The algorithm calculates the maximum number of bits required to store the largest delta in the block (the "frame").
*   **PForDelta**: A variation used in Lucene handles outliers (exceptions) separately, ensuring that a single large delta does not force the entire block to use a high bit-width.

**Roaring Bitmaps**
For caching filter results in memory, Elasticsearch employs Roaring Bitmaps. This hybrid data structure dynamically adapts:
*   **Sparse Containers**: If a container holds fewer than 4,096 integers, it uses a sorted array of 16-bit integers.
*   **Dense Containers**: If it holds more, it switches to a bitmap representation.
*   **Run-Length Encoding (RLE)**: Used for sequences of continuous integers.

### 1.3 The BKD Tree Revolution
Prior to version 5.0, Elasticsearch indexed numeric data using Tries. The introduction of **BKD Trees (Block K-D Trees)** fundamentally altered the engine's capabilities.
*   **Structure**: A balanced tree structure optimized for block-based storage (like a B-Tree), organizing points in N-dimensional space.
*   **Performance**: Extremely efficient for range queries and nearest-neighbor searches.
*   **Geo-Spatial Optimization**: For geospatial data, Elastic implemented **Selective Indexing**. In high-dimensional scenarios, the tree construction is driven by the first $k$ dimensions, effectively creating an R-Tree structure for precise spatial filtering with minimal disk I/O.

## 2. Distributed Architecture

### 2.1 Zen2 Consensus
In version 7.0, Elastic introduced **Zen2**, a completely rewritten cluster coordination layer (deterministic algorithm).
*   **Voting Configurations**: Decouples the set of nodes that can elect a master from the set of active nodes.
*   **Term and Epochs**: Uses a "Term" counter to order changes; a master from a higher term supersedes one from a lower term.
*   **State-Based vs. Log-Based**: Zen2 replicates the cluster state itself. When a master updates the state, it calculates the diff (delta) and publishes it.

### 2.2 Replication and Soft Deletes
*   **Primary-Replica Model**: Writes go to Primary, then forwarded in parallel to In-Sync Replicas (ISR).
*   **Soft Deletes**: To enable **Cross-Cluster Replication (CCR)**, Soft Deletes maintain "tombstones" of deleted documents. This allows the leader to replay operations (including deletions) to a lagging follower, ensuring eventual consistency even after segment merges.

### 2.3 The Translog
To provide real-time search without sacrificing durability:
1.  **Operation**: Document is indexed into in-memory buffer and appended to Translog file.
2.  **Refresh**: Buffer is "refreshed" into a new segment (searchable, not fsync'ed).
3.  **Fsync Policy**: Translog is fsync'ed to disk before acknowledging the write request. On crash, Translog is replayed.

### 2.4 Tiered Merge Policy
Elasticsearch uses `TieredMergePolicy` to manage segment counts.
*   **Skew Optimization**: Favors merging segments of approximately equal size.
    $$\text{Skew} = \frac{\text{Size of Largest Segment}}{\text{Size of Smallest Segment}}$$
*   **Cost Function**: Minimizes a cost function considering total size, skew, and deleted documents ratio. This prevents "merge storms."

## 3. Underlying Technologies

### 3.1 JVM Mechanics: G1GC
Elasticsearch requires careful memory tuning.
*   **Garbage Collection**: Defaults to **G1GC** (Garbage First GC).
*   **Humongous Objects**: Large objects (>50% region size) are allocated in contiguous regions, which can cause heap fragmentation with Elasticsearch's usage patterns (e.g., large arrays for aggregations).

### 3.2 Netty and Non-Blocking I/O
The transport layer uses **Netty**.
*   **Zero-Copy**: Uses Direct Memory (off-heap buffers) to move data from network card to application memory without intermediate copies.
*   **The Recycler**: An object pooling mechanism for off-heap buffers, crucial for high-throughput, low-latency requirements.
