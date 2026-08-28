# ADR-0010: Concurrency Safety — Deferred Locking for Exactly-Once Operations

## Status
Accepted

## Context

A test firing two concurrent ainvoke calls on one thread_id showed the final step_count
was 2 instead of the expected 3, because both concurrent invocations read the same base
checkpoint before either committed.

step_count, using operator.add, tolerates concurrent writers — deltas merge, and the value
converges correctly; the transient 2-not-3 is read-timing skew, not a true lost update.
But pending_approval uses the default overwrite reducer; two concurrent writers to it would
genuinely lose an update, because the second write replaces the first rather than merging.
No operation writes pending_approval concurrently yet, so the lock is deferred to Module 6.

## Decision

We defer building a concurrency lock until Module 6, when HITL introduces the first
operation that must run exactly once — a human approval on pending_approval, where two
concurrent writers must not both succeed.

Delta-reducer fields (operator.add, add_messages) need no lock because concurrent deltas
merge instead of overwriting; many writers are safe by design.

The lock, when built, will use Redis as the lock store (per the persistence architecture:
Postgres = durable system of record, Redis = ephemeral locks and cache only).

## Consequences

Until the lock lands, overwrite fields (pending_approval) are unprotected under concurrent
writes. This is acceptable because no current operation writes them concurrently — the only
concurrent writers today touch delta fields, which are safe.

If an exactly-once operation shipped before the lock, pending_approval could be written by
two workers at once and one approval could be silently lost — an audit and correctness
failure for regulated customers.

When the lock lands, a test asserting serialized writes converge correctly
(test_concurrent_serialized_with_lock, expecting 3) must accompany it.

## Trigger

This ADR reactivates in Module 6, when HITL adds a write path to pending_approval (an
overwrite field) that more than one worker or request can reach — because an approval is
an exactly-once operation and an overwrite reducer cannot protect it alone.

## References
- ADR-007 — control-plane fields (pending_approval, status)
- ADR-009 — schema freeze
- tests/test_checkpointer.py::test_concurrent_lost_update_without_lock
- Module 6 — HITL