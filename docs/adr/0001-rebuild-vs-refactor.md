# ADR-001: Rebuild rather than refactor the capstone prototype

## Status
Accepted

## Decision
Build the platform fresh in this repo. Archive the IITM Pravartak capstone as a
read-only reference prototype — do not refactor it in place, do not delete it.
Salvage: domain, tool concepts, 10 eval cases, RAG corpus. Rebuild: state model,
agent wiring, persistence, orchestration.

## Notes
Full context, alternatives, and consequences to be expanded before the repo goes
public. Refactor-in-place (issue #1) was rejected: can't cleanly preserve intent
in code that was never internalized.