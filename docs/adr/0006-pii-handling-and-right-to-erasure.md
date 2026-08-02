# ADR-006: PII Handling and Right-to-Erasure

## Status
Accepted

## Context
GDPR(General Data Protection Regulation) says erase the customer's personal data; financial/audit rules say RETAIN the transaction record. In a naive checkpoint design these are the
SAME rows. Now if the checkpoint is deleted we loose the audit trail for financial transactions. 

This ADR resolves it by separating identity from the record.

## Decision
PII is handled in two categories:

Structured PII (customer_id → name/email/address):Two tables will be used, The thread-metadata table is to store thread_id → customer_id → topic_id and The customer PII table is for storing customer_id → name/email.
Deletion removes the row in customer PII table and keeps the mapping in thread-metadata table

Unstructured PII (personal data the customer TYPED into messages, frozen in
checkpoint state): For personal data in messages we tokenize each personal information and put that in the message, keep the token value mapping in a separate vault table. Checkpoints stores only tokens never the raw PII

Erasure mechanism:
Delete the vault entry → every token across all checkpoints orphans at once. So checkpoints are never edited, it is append-only and that preserves immutability.

Fallback:
For the raw PII Mask-on-erasure will be applied. This is never a primary path a fallback mechanism

## Rationale
The tokenize at the ingestion time gives clear way of identifying and catching them at the first time, detecting is a time consuming and error prone process

The data is kept in separate tables for easier delete, when ever we need the data to show it is easier to reproduce and when delete is required, every information remains in a single table which is easier to find and delete.Compared to irreversible [REDACTED] masking that would be easier

The principle that ties Block 4 together: retention & deletion are
DESIGNED at the start, in the state model — not bolted on at the end.


## Consequences
The vault becomes the single most security-critical table — the one
place re-identification is possible. It needs to have strongest access control, it has the possibility of getting deleted, so need to be protected from that.
Editing append-only checkpoints (the mask-on-erasure fallback) is a
privileged, audited exception — who erased, when, under what request.
PII detection is never 100%; this is an ongoing, imperfect problem

## Alternatives Considered
- Delete-by-thread (DELETE WHERE thread_id=X): rejected — shatters the parent chain, destroys the audit record you're required to keep.
- Irreversible in-place masking as primary: Vault approach is better than this because the data remain in a central place, locating and deleting is easy