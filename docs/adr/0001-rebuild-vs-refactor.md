# ADR-0001: Rebuild rather than refactor the capstone prototype

**Status:** Accepted

## Context

`retail-ai-support-agent` was an IITM Pravartak capstone, built in roughly ten
hours against a deadline. It works. It also has two problems that matter more
than whether it works.

**Structural.** One file mixes five concerns: database access, tool definitions,
agent construction, safeguards, and the CLI. There are no service boundaries to
refactor toward, because there are no services.

**Epistemic, and this is the deciding one.** The code was pasted, not
internalized. Refactoring preserves code you do not understand. It moves it into
better-shaped files and leaves the gap in place — now hidden behind structure
that looks deliberate.

The purpose of this project is mastery, not a working demo. Those two goals
prefer different decisions here.

Issue #1 on the old repo proposed an in-place refactor. Its diagnosis was
correct. Its prescription is superseded by this ADR.

## Decision

Build the platform fresh in this repo. Archive the capstone as a read-only
reference prototype — do not refactor it in place, do not delete it.

**Salvage:** domain knowledge, tool concepts, the 10 evaluation cases, the RAG
corpus.

**Rebuild:** state model, agent wiring, persistence, orchestration.

The distinction is deliberate. Salvaged items are artifacts whose correctness
does not depend on the architecture around them. Rebuilt items are exactly the
things that were never decided — they were inherited from a LangGraph prebuilt
that made those decisions invisibly.

## Consequences

**Paid**

- Slower start. There is no runnable system for several modules.
- Work that already exists gets written again.

**Gained**

- Every architectural decision is made explicitly and recorded, rather than
  inherited from a library default.
- Service boundaries exist from the first commit instead of being retrofitted.
- The capstone remains available as a reference and as evidence of progression.

## Why archive rather than delete

It is honest provenance. The capstone is where the domain understanding came
from, and the distance between the two repos is itself worth showing.
