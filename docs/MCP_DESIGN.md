# MCP — Audit Result and Binding Design Constraints

> **Status:** Design note, 2026-06-10. Audit verdict first, constraints
> second. No MCP code exists in the skeleton today; this note binds any
> future MCP work to the protocol's 2026-07-28 release-candidate state
> so the skeleton never ships against deprecated surface.
> **Companion docs:** [`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md)
> (same evidence-before-build discipline),
> [`REENTRANCE.md`](REENTRANCE.md).

## 1. Audit result (2026-06-10)

Repo-wide sweep over `src/`, `tests/`, `examples/`, `docs/`:

- **`src/organism/` contains no MCP module and no MCP dependency.**
  There is nothing to migrate and nothing that the 2026-07-28 MCP
  release candidate can break.
- The string "MCP" appears only in forward-looking documentation:
  the adapter module README names an MCP adapter as a possible future
  bridge, `ARCHITEKTUR/01_ANATOMIE.md` lists "effector as MCP server"
  as an optional exposure, `ARCHITEKTUR/09_FRAMEWORK.md` and
  `02_NERVENSYSTEM.md` mention MCP as one interface option among
  capabilities schemas.
- Verdict: **the audit closes with a design constraint, not a
  migration.** The mentions stay (they describe a real, still-valid
  option); this note is what they now point to.

## 2. Binding constraints for any future MCP adapter

The MCP release candidate (final 2026-07-28) makes the protocol core
stateless and deprecates several v1 features. Any MCP adapter built
on this skeleton — by us or by a consumer — follows these rules:

1. **Stateless by design.** No reliance on an `initialize` handshake
   or a session ID. Every request carries what it needs. This matches
   the skeleton's own grain: effectors are constructed per call-site,
   stores are the durable state, the protocol layer holds nothing.
2. **Deprecated surface is off-limits.** Roots, Sampling, and
   Logging are deprecated in the RC and are not to be used — not even
   "temporarily". A skeleton adapter that leans on deprecated
   protocol features is a liability with a known expiry date.
3. **Async work targets MCP Tasks.** Tasks graduated from
   experimental in the RC. Long-running effector work exposed over
   MCP maps to a Task, not to a homegrown polling or session scheme.
   (This composes with the reserved reentrance pattern: a paused plan
   would surface as a task awaiting input, not as protocol state.)
4. **Elicitation only during active request processing.** The RC
   constrains elicitation to in-flight requests. The natural mapping
   for this skeleton: **Plan-Gate approval as MCP Elicitation**
   (form mode, JSON schema = the plan's approval descriptor). This is
   the one place where our HITL gate could become visible to foreign
   MCP clients without a custom UI. Design-level mapping only — the
   explicit Plan/HITL/Dispatch production default
   ([`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md)) applies, and
   nothing gets built ahead of a consumer that needs it.

## 3. Why no adapter ships today

Same trigger discipline as everywhere else in the skeleton: the
adapter README has named MCP as an option since phase 1, no consumer
has needed it, and building it on spec would have meant shipping code
in June that the July RC deprecates. The cheapest correct MCP adapter
is the one written *after* the RC is final, against these
constraints, when a real consumer asks for one.

The constraints are domain-free by construction (separation test:
a tax practice exposing its effectors over MCP faces exactly the same
four rules), so this note lives in the public docs rather than in any
consumer's repo.
