# Receipted Transfer — Auditable Hand-offs Between Semi-Autonomous Tools

> **Status:** Pattern chapter, 2026-06-10. Documentation only — the
> skeleton ships no `transfer` module; consumers assemble the pattern
> from existing parts (Plan-Gate, EventBus, Provenance, stores).
> Name checked against prior art before adoption: "handoff" denotes
> *control* transfer between agents (OpenAI Agents SDK, Microsoft
> Agent Framework, LangGraph); "message ferrying" is established
> DTN-networking vocabulary. **Receipted Transfer** names something
> neither covers: a *data/write* transfer whose completion is proven
> by an auditable receipt. (Internally the pattern grew up under the
> nickname "ferry".)
> **Companion docs:** [`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md),
> [`OBSERVABILITY.md`](OBSERVABILITY.md), [`LIFECYCLE.md`](LIFECYCLE.md).

## 1. The problem

In a multi-tool system with a shared file truth, tools constantly
move data into each other's territory: a watcher turns an inbound
document into a task, a meeting protocol becomes a todo with an
owner and a due date, a review result lands in another tool's status
field. Each of these is a **transfer**: source tool, target tool,
one operation, one payload.

Transfers fail differently than actions. An action that fails
usually fails loudly — an exception, a validation miss, a denied
gate. A transfer can fail **silently**: the routing layer simply
never dispatches the operation, the target writes a slightly
different schema than the source assumed, the success signal you
trusted turns out to be a test artifact. Nothing crashes. The data
is just not there, or not traceable, and nobody notices until a
human asks "where did that come from?"

## 2. The pattern — six contract elements

A receipted transfer is a transfer that carries a **contract** and
leaves a **receipt**. Six elements, each independently cheap, jointly
closing the failure classes in section 3:

1. **Transfer contract.** Every route is declared: source, target,
   operation, payload schema. A transfer that is not declared does
   not exist — there is no "implicit" route.
2. **Receipt (data trail).** Every executed transfer appends one
   event to an append-only trail: route, payload digest, outcome,
   timestamp. The receipt is written by the *transfer machinery*,
   not by the business code — so its absence is meaningful.
3. **Fail-loud registry.** Dispatch goes through a registry keyed by
   route. An operation arriving for an unwired route raises — loudly,
   immediately. Never a silent no-op, never a warning that scrolls by.
4. **Drift check.** The payload schema is asserted on **both** sides:
   the source validates what it sends, the target validates what it
   receives. Two tools that drift apart (one expects a long-form
   identifier, the other a short form) fail the check instead of
   half-writing.
5. **Provenance propagation.** The provenance block travels with the
   payload **end to end** and is persisted at the target — in the
   target's own truth store (e.g. the entity's frontmatter), not just
   in the sender's log. Where the target has no provenance field, the
   transfer layer must say so explicitly rather than dropping it.
6. **Gate hook.** Transfers that write pass through the Plan-Gate
   like any other side effect ([`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md)):
   propose → human approve → dispatch. Read-only transfers skip the
   gate, exactly like queries skip the action ceremony.

None of this requires new framework machinery. The contract is a
dataclass, the receipt is an EventBus event plus an append-only
store, the registry is a dict with a raising default, the drift
check is the existing validator pointed at a payload schema, the
provenance container already exists, and the gate is the gate.
**The pattern is a discipline, not a dependency.**

## 3. Empirical failure taxonomy

The taxonomy below comes from a production case study: one consumer
system, twelve transfer routes mapped, nine verified live end-to-end
during a structured real-world test (the remaining routes had no
production counterpart yet — itself a finding, see failure class 1).
Domain specifics are anonymized; every failure class generalizes
(separation test: each one occurs identically between, say, a
receipt-classifier and a bookkeeping tool in a tax practice, or
between a forecast tool and an ERP in a CFO office).

| # | Failure class | What it looks like | Closed by |
|---|---|---|---|
| 1 | **Silent no-op** | The routing layer never dispatches the operation; logs stay quiet; callers assume success | (3) fail-loud registry — unwired route raises; (2) receipt — a missing receipt is detectable |
| 2 | **Schema drift between arms** | Source sends a long-form identifier, target resolves short-form (or vice versa); writes land in the wrong place or nowhere | (4) drift check on both sides; (1) declared payload schema per route |
| 3 | **False-positive receipt** | The "it worked" signal is a test artifact or a stale file, not an organic event from the live path | (2) receipt written only by the transfer machinery on the live path, append-only, with payload digest |
| 4 | **Missing provenance at target** | The write succeeds but the target record cannot answer "who wrote this, from what source, with what confidence" | (5) provenance propagation into the target's truth store; explicit error where the target has no field |
| 5 | **Swallowed errors** | A sub-step fails (e.g. an embedding or index update) and is logged as a warning while the transfer reports success | (3) fail-loud discipline extended to sub-steps: partial success is a distinct receipt outcome, never a clean one |

The case study's blunt lesson: **four of the five classes produce no
exception.** Only contract elements that make *absence* visible
(receipts, fail-loud registries, both-sided schema checks) catch
them — after-the-fact log reading does not.

## 4. Positioning

- **MCP / A2A** are request protocols: they standardize how a client
  invokes a tool or how agents talk. They do not say what a
  *completed data transfer* must leave behind. A receipted transfer
  can run **over** MCP or A2A.
- **OpenLineage** (and pipeline-lineage tooling generally) records
  dataset-level lineage for batch pipelines — without agent context,
  per-action gates, or human approval semantics.
- **Agent handoff patterns** transfer *control and conversation
  context* between agents; the receipted transfer moves *data into a
  foreign truth store* and proves it.

The contract for auditable agent-to-tool data transfer — receipt,
both-sided schema, propagated provenance, gated writes — is, as far
as we can establish, unoccupied territory. This chapter stakes it
out as a pattern; the skeleton's existing primitives are sufficient
to implement it.

## 5. Cross-domain shape (separation test)

- **Tax practice:** receipt classifier → bookkeeping tool. Route
  `classifier→ledger:post_draft`, payload schema with mandate
  reference (drift risk: mandate ID long/short form), receipt per
  posting draft, provenance into the posting record, gate before
  anything touches the ledger.
- **CFO office:** forecast tool → ERP. Route
  `forecast→erp:update_plan`, schema with cost-center key, receipt
  per plan update, provenance into the plan line, gate on write.
- **Design office:** document watcher → task tool. Route
  `watcher→tasks:create_item`, schema with entity reference, receipt
  per created item, provenance into the item's frontmatter, gate on
  write.

Three domains, identical six elements, identical failure classes.

## 6. What the skeleton does NOT do

No `organism.transfer` module ships, deliberately. The pattern
composes from existing parts, and the production default
([`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md)) applies to its
gate hook. If a second consumer implements the pattern and the
composition turns out to repeat itself mechanically, *that* is the
evidence trigger for lifting a helper into the skeleton — the same
discipline as every other reserved pattern here.
