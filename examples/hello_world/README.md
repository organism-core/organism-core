# hello_world — minimal pipeline walk

The smallest possible organism-core demo: **one effector, one entity,
one propose → approve → apply cycle**. About 60 lines of domain code,
the rest is the generic pipeline.

Use this as the first thing to read after the
[`README`](../../README.md) — and as the template to copy when wiring
your own domain.

## Run it

```bash
# from the repo root
python -m examples.hello_world
```

You'll see the four-section walk:
- `[SETUP]` — store wiring (entity, plan, lifecycle, lessons, traces)
- `[SEEDING]` — one entity written with three DoD criteria
- `[PIPELINE]` — `execute()` → `approve()` → `apply_approved_plan()`
- `[VALIDATION]` — per-criterion result breakdown

## The two run modes

| Mode | When | What changes |
|---|---|---|
| **Deterministic** (default) | No env var set | The `friendly_tone` criterion is evaluated by `self_check` — the effector self-attests. Always green, no network, no cost. |
| **LLM judge** | `ANTHROPIC_API_KEY` is set | `friendly_tone` switches to `llm_judge` — an Anthropic Claude Haiku 4.5 call decides whether the greeting is actually friendly. This is the pattern's real selling point. |

To try the LLM mode:

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # macOS / Linux
$env:ANTHROPIC_API_KEY="sk-ant-..."      # PowerShell on Windows

pip install organism-core[llm]           # picks up the optional dep
python -m examples.hello_world
```

The cost per run is fractions of a cent (single 8-token Haiku call).

## What's in the box

```
examples/hello_world/
  effector.py    HelloGreeter — returns a greeting dict, ~30 lines
  demo.py        run_demo() — pipeline wiring + narration, ~180 lines
  __main__.py    CLI entry point
  __init__.py    package exports
```

## The entity (declarative DoD)

```yaml
type: greeting
dod:
  criteria:
    - name: mentions_name      # rule (deterministic equality)
      expected: true
      weight: 1.0
    - name: length             # rule (numeric range)
      expected: "5..200"
      weight: 0.5
    - name: friendly_tone      # self_check OR llm_judge
      expected: true
      weight: 0.8
      evaluator: llm_judge     # or "self_check" in deterministic mode
```

The criteria are graded independently and weighted; the final
`score = sum(weight if satisfied) / sum(all weights)` is the
`Fulfillment Score`. The lifecycle stage transitions are driven by
the score history — but this demo deliberately runs only one
iteration, to keep the trace short.

## What the LLM judge actually does

The judge sees the full result dict, not just the actual value. The
prompt is intentionally narrow ("YES or NO, one word"):

```python
def judge(criterion, actual, result) -> tuple[bool, str]:
    greeting = result["greeting"]
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=8,
        messages=[{
            "role": "user",
            "content": f"...is the greeting below friendly?\n\nGreeting: {greeting!r}\n\nAnswer YES or NO."
        }],
    )
    verdict = message.content[0].text.strip().upper()
    return (verdict.startswith("YES"), f"llm_judge: {verdict}")
```

The judge can never be gamed by the effector — the effector returns
the raw text, the judge looks at it independently. Compare to
`self_check`, where the effector attests its own friendliness in the
result dict (cheaper, but trust-based).

## How to extend this

1. **More criteria.** Add to the entity frontmatter. Each criterion
   picks its own evaluator. Mix rule, self_check, and llm_judge
   freely.
2. **Your own effector.** Copy `effector.py`, change `name`, return
   whatever you want in `act()`. The DoD engine reads the entity's
   declared criteria — your effector just has to populate the
   matching keys in its return dict.
3. **Real LLM workflows.** Replace `HelloGreeter` with an effector
   that calls an LLM for the actual action (translation, extraction,
   summarization, classification). The `llm_judge` criterion then
   validates the LLM's own output.
4. **Multi-iteration.** Remove the `set_stage` calls — let the
   lifecycle promote naturally after `promote_after_n` (default 30)
   successful actions. See [`tax_lite`](../tax_lite/) for a longer
   walk.

## What this demo deliberately omits

- **Lessons feedback loop.** Look at [`tax_lite`](../tax_lite/) or
  [`architect_lite`](../architect_lite/) for the AUTONOMOUS revision
  loop and lesson recording.
- **Querier path** (read-only tools). See
  [`tax_lite/querier.py`](../tax_lite/querier.py) for the parallel
  read-only lineage.
- **Cockpit UI events.** See [`cockpit_demo`](../cockpit_demo/) for
  the headless render schemas.
- **Multiple entities + cross-domain genericity proof.** See the
  three domain demos and their cross-domain test.

Each of those is one logical step further. Start here, walk outward.
