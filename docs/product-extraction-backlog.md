# Product Extraction Backlog

Future commercial products to extract from `retail-support-platform`.

**Status: parked.** Do not build now. Revisit at the framework-extraction
milestone — only after the platform is built and the same patterns have
repeated across two or more projects.

## 1. Agent Governance / Trust Layer

Approval gates, full audit trail, and right-to-be-forgotten PII erasure for
agentic systems. Extracted from Block 5 (HITL) and ADR-006 (PII erasure).

Wedge: narrow, compliance-driven, sells on enterprise-architecture
credibility into regulated buyers (healthcare, finance, insurance).

## 2. Durable HITL-as-a-Service

Drop-in approval control plane: dormant-row durability, TTL / abandonment,
resume, audit. Shape: OSS core + hosted dashboard. Extracted from the Block 5
HITL primitive.

---

_Selection principle for future ideas: a good wedge is (a) narrow, (b) a
painful production problem — not a demo feature, (c) something enterprise
credibility uniquely sells, and (d) extractable from work already underway._
