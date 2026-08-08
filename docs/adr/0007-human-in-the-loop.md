# ADR-007: Human-in-the-Loop Control

## Status
Accepted

## Context
Some agent actions are irreversible and high-blast-radius (refunds, account changes); an LLM
proposing them is not enough; a human must approve before they execute 

## Decision
The platform pauses the graph for human review at designated points. The
mechanism has four parts:

### 1. Pause durability
A paused graph is actually a record at the database, not a
blocked process. It reuses the crash-resume checkpoint mechanism (ADR-005) 
Rationale: its a record in database so if it is 1000 connections or tens of thousand, it just another record in the database and that's how it is easy to scale

### 2. Response taxonomy
A reviewer can accept/reject/edit. Carried out of interrupt() via Command(resume=...) as a single structured payload.
Rationale: The three because user can accept, reject or can propose a new value that's why edit

### 3. Reject routing
On reject, control returns to the supervisor, expressed as state (a rejection flag + reason written into state), not as a new direct edge.
Rationale: ADR-004 made the supervisor the single routing authority. If reject created a direct edge to another worker, we'd have a second router and lose that guarantee. Instead the reject writes its outcome into state; the supervisor reads it and routes onward. One router stays in charge, and every routing decision remains auditable in one place.

### 4. Abandonment (TTL)
A scheduled job outside the graph scans Postgres for threads paused past a TTL and issues an auto reject. 
The "auto reject" is not a new path.This reuses the reject path above — the clock issues the same verdict a human would.
Rationale: The graph is asleep and cannot watch itself; a sleeping process can't wake itself on a timer. So the watcher must be an external process that never slept.
Safety: pre-interrupt work is only calculation — no data changed — so an abandoned thread is safe to discard (see ADR-008).

## Consequences
Positive: For high valued decisions Human has a much better judgement than a LLM prediction
Negative / cost: The process will be slower, many graph may remain unanswered, redundant data, required a TTL job to finally end it gracefully
Note: abandonment-safety and resume-safety both depend on ADR-008. If side effects ever move before interrupt(), both break.

## Related
- ADR-004 (routing authority — reject routing depends on it)
- ADR-005 (checkpointer — durability reuses it)
- ADR-008 (irreversibility barrier — makes abandonment safe)