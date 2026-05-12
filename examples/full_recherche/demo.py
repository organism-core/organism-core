"""Full DoD-Recherche demo --wires up all 6 sources with synthetic
content to show the M5 hierarchy in action.

Unlike architect_lite/tax_lite/cfo_lite (which focus on the lifecycle
pipeline), this demo focuses on the *recherche* itself: how 6 sources
contribute criteria to a single DoD before any action runs.

The 3 stub sources in the Skelett (``RelatedEntitiesSource``,
``VectorSearchSource``, ``DomainPatternSource``) are plug-points for
consumers; this demo provides minimal generic implementations to show
how they would be wired up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from organism.dod import (
    Criterion,
    DoDEngine,
    DoDEngineSettings,
    EntityFrontmatterSource,
    LessonsSource,
    UserClarificationSource,
)
from organism.lessons import LessonsAggregator, LessonsStore
from organism.memory import Entity, EntityStore

from examples.full_recherche.sources import (
    PatternRegistrySource,
    RelatedEntitiesScanSource,
    StaticVectorSearchSource,
)

KIND = "full_recherche_demo"
PrintFn = Callable[[str], None]


@dataclass
class FullRechercheSummary:
    primary_seeded: bool = False
    siblings_seeded: int = 0
    lesson_pre_seeded: bool = False
    sources_count: int = 0
    sources_contributing: int = 0
    total_criteria: int = 0
    final_confidence: float = 0.0
    contributions_per_source: dict[str, int] = field(default_factory=dict)


def run_demo(
    output_dir: Path,
    print_fn: PrintFn = print,
) -> FullRechercheSummary:
    summary = FullRechercheSummary()

    print_fn("")
    print_fn("==============================================================")
    print_fn("  full_recherche -- DoD-Recherche-Walk durch alle 6 Quellen")
    print_fn("==============================================================")
    print_fn("")

    # ---- Setup ----
    print_fn("[SETUP]")
    entity_store = EntityStore(output_dir / "entities")
    lessons_store = LessonsStore(output_dir / "lessons")
    aggregator = LessonsAggregator(store=lessons_store)

    # Seed primary entity (the request target) with one frontmatter criterion.
    entity_store.write(
        "task-primary",
        Entity(
            frontmatter={
                "type": "alpha",
                "subtype": "first",
                "dod": {
                    "criteria": [
                        {
                            "name": "doc_present",
                            "expected": True,
                            "weight": 1.0,
                        },
                    ]
                },
            },
            body="",
        ),
    )
    summary.primary_seeded = True

    # Seed sibling entities with the same type+subtype.
    # The RelatedEntitiesScanSource will harvest their criteria.
    siblings = {
        "task-sibling-a": [
            {"name": "doors_aligned", "expected": True, "weight": 0.6},
        ],
        "task-sibling-b": [
            {"name": "doors_aligned", "expected": True, "weight": 0.6},
            {
                "name": "footprint_within_envelope",
                "expected": True,
                "weight": 0.5,
            },
        ],
    }
    for sibling_id, criteria_specs in siblings.items():
        entity_store.write(
            sibling_id,
            Entity(
                frontmatter={
                    "type": "alpha",
                    "subtype": "first",
                    "dod": {"criteria": criteria_specs},
                },
                body="",
            ),
        )
        summary.siblings_seeded += 1

    # Pre-seed a lesson --simulates a prior dod-failure that bequeaths a
    # criterion to future actions of the same kind in matching context.
    aggregator.record_lesson(
        kind=KIND,
        observation=(
            "prior dod-failure: alignment-check often missed in first-batch"
        ),
        criteria_hint=[
            Criterion(
                name="alignment_verified",
                expected=True,
                weight=0.5,
                source="dod_failure",
            )
        ],
        confidence_delta=0.1,
        context_pattern={"type": "alpha"},
    )
    summary.lesson_pre_seeded = True

    print_fn(
        f"  primary entity:    task-primary (1 frontmatter criterion)"
    )
    print_fn(
        f"  sibling entities:  {summary.siblings_seeded} "
        "(matched on type+subtype)"
    )
    print_fn(
        "  pre-seeded lesson: alignment_verified "
        "(via prior dod_failure)"
    )
    print_fn("")

    # ---- Engine assembly ----
    print_fn("[ENGINE ASSEMBLY]")

    def _custom_questions(request, context, current):
        # Trigger the user-clarification fallback only when no upstream
        # source contributed any criteria. With the wiring below, upstream
        # always supplies criteria --so this returns [] and user_clarification
        # contributes nothing visible.
        return [] if current.criteria else [
            "DoD could not be derived --user input required"
        ]

    sources = [
        EntityFrontmatterSource(store=entity_store),
        LessonsSource(aggregator=aggregator),
        RelatedEntitiesScanSource(
            store=entity_store,
            match_keys=["type", "subtype"],
        ),
        StaticVectorSearchSource(
            index={
                KIND: [
                    {
                        "name": "spec_present",
                        "expected": True,
                        "weight": 0.4,
                    },
                    {
                        "name": "naming_consistent",
                        "expected": True,
                        "weight": 0.3,
                    },
                ]
            }
        ),
        PatternRegistrySource(
            patterns={
                "alpha": [
                    {
                        "name": "occupancy_class_set",
                        "expected": True,
                        "weight": 0.3,
                    },
                ]
            },
            pattern_key="type",
        ),
        UserClarificationSource(generate_questions=_custom_questions),
    ]
    summary.sources_count = len(sources)
    for source in sources:
        print_fn(f"  + {source.name}")
    print_fn(
        "  Engine threshold = 99.0 (suppresses early-exit so every "
        "source runs)"
    )
    print_fn("")

    engine = DoDEngine(
        sources=sources,
        # Threshold above any reachable confidence => no early-exit.
        # In production: leave at default 0.8.
        settings=DoDEngineSettings(threshold=99.0),
    )

    # ---- Recherche ----
    print_fn("[RECHERCHE] engine.derive() ...")
    dod = engine.derive(
        request="task-primary",
        context={
            "kind": KIND,
            "entity_id": "task-primary",
            "type": "alpha",
            "subtype": "first",
        },
    )
    print_fn("")

    # ---- Per-source breakdown ----
    print_fn("[SOURCE-CONTRIBUTIONS]")
    referenced = set(dod._provenance.keys())
    for source in sources:
        criteria_names = dod._provenance.get(source.name, [])
        if criteria_names:
            print_fn(
                f"  {source.name}: {len(criteria_names)} criteria --"
                f"{', '.join(criteria_names)}"
            )
            summary.contributions_per_source[source.name] = len(
                criteria_names
            )
            summary.sources_contributing += 1
        elif source.name in referenced:
            print_fn(
                f"  {source.name}: 0 criteria (evidence-only contribution)"
            )
        else:
            print_fn(
                f"  {source.name}: did not contribute "
                "(fallback or no match)"
            )
    print_fn("")

    # ---- Final assembled DoD ----
    print_fn("[FINAL DoD]")
    print_fn(f"  Total criteria:       {len(dod.criteria)}")
    print_fn(f"  Final confidence:     {dod.confidence:.3f}")
    print_fn(
        f"  Clarification needed: {dod.clarification_needed or 'none'}"
    )
    print_fn("  Criteria  (name :: source-stamp :: weight):")
    for c in dod.criteria:
        print_fn(
            f"    {c.name} :: {c.source} :: weight={c.weight}"
        )
    print_fn("")

    summary.total_criteria = len(dod.criteria)
    summary.final_confidence = dod.confidence

    # ---- Summary ----
    print_fn("[SUMMARY]")
    print_fn(f"  sources wired:        {summary.sources_count}")
    print_fn(f"  sources contributing: {summary.sources_contributing}")
    print_fn(f"  total criteria:       {summary.total_criteria}")
    print_fn(f"  final confidence:     {summary.final_confidence:.3f}")
    print_fn("")

    return summary
