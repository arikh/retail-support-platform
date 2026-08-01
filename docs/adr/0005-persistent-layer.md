# ADR-005: Persistence Layer — Postgres as System of Record, Redis for Ephemeral Coordination

## Status
Accepted

## Context
we have several distinct storage jobs, and the tempting move is to ask "which database should we pick?" — which is the wrong question, because different jobs want different tools.We have to store checkpoints and metadata in a durable storage, so that they can be fetched later. Need vector storage for Rag. The system also need to keep data in cache and manage locks. So there are a quite a few requirements which has different expectations.


## Decision
Postgres is the system of record:
- Durable checkpoints (PostgresSaver)
- Thread-metadata table (thread_id → customer_id → topic_id → created_at)
- Vector storage via pgvector, behind a VectorStore interface

Redis is ephemeral coordination only:
- Distributed locks (one process per thread_id)
- Caching (hot supervisor-routing lookups)
- Never the checkpointer; never a system of record

## Rationale
- Checkpoint data needs to be durable, a persistent storage like Postgres is required so that the data is not lost due to crash which is a possibility for Redis as it stores data in memory
Redis will be used for cache and locks which has a TTL and durable data and ephemeral data don't share a store.
PGvector because, the data what we have is low, postgres is already getting used, minumim tools minimum headaches to manage them. For GDPR delete, lesser tool will be better as less place to find for delete


## Consequences
All three now lives in PostGres, it is simpler to manage backup and security. But it is becoming a SPOF. So managing it is critical.Now deleting GDPR data will involve deleteing all the personal data of the user.

## Alternatives Considered
We considered Postgres for permanent storage and kept redis for cache and locks. There was a choice of choosing redis for all but I discarded that seeing the nature of data and the durability.
For vector database there were multiple choice like PineCone or Chroma, but I sticked to PGVector, as the data size is limited for now, and Postgres is already getting used. 
If I see the datasize is increasing significantly and it is getting difficult for PGVector to manage it, we will switch to any other vector database which supports larger scale
