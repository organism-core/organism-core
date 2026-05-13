"""Domain-pattern source — generic registry of canonical criteria
sets, keyed by ``(action_type, entity_type)``.

The skeleton ships only the registry interface and the lookup
mechanism. Domain-specific knowledge (which patterns apply where)
lives in the consumer's setup code, not in ``organism-core``.

Two lookup modes are supported, each as its own source instance so
that the engine emits separate provenance buckets:

- ``MODE_TUPLE``: lookup by ``(action_type, entity_type)``. Provenance
  bucket ``domain_pattern:tuple``. Narrowest scope — highest
  specificity. Used when the request context carries both keys.
- ``MODE_ACTION_ONLY``: lookup by ``action_type`` alone (``entity_type
  = None`` key in the registry). Provenance bucket
  ``domain_pattern:action_only``. Broader scope, applies regardless of
  the entity type. Used as a baseline of action-typical criteria.

Consumers typically register both kinds of patterns in one registry
and wire both source instances via :func:`default_sources`. A consumer
that only cares about one mode passes a single instance with the
matching ``lookup_mode``.

Stub semantics: calling ``DomainPatternSource()`` with no registry
returns an empty contribution and writes no provenance — required for
the protocol-compliance tests.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from organism.dod.settings import DomainPatternSettings
from organism.dod.types import Criterion, DoD, SourceContribution

CONTEXT_KEY_ACTION_TYPE = "action_type"
CONTEXT_KEY_ENTITY_TYPE = "entity_type"


class PatternRegistry:
    """In-memory registry of canonical criteria per
    ``(action_type, entity_type)`` key.

    ``entity_type=None`` is a first-class key — it represents the
    "applies to any entity_type" pattern, looked up by
    :class:`DomainPatternSource` in ``MODE_ACTION_ONLY``.

    Registration is additive: multiple calls with the same key append
    criteria. To replace, call :meth:`clear` first.
    """

    def __init__(self) -> None:
        self._patterns: dict[
            tuple[str, str | None], list[Criterion]
        ] = {}

    def register(
        self,
        *,
        action_type: str,
        entity_type: str | None = None,
        criteria: list[Criterion],
    ) -> None:
        if not action_type:
            raise ValueError("action_type must be non-empty")
        if not isinstance(criteria, list):
            raise TypeError(
                f"criteria must be a list, got {type(criteria).__name__}"
            )
        for c in criteria:
            if not isinstance(c, Criterion):
                raise TypeError(
                    f"criteria entries must be Criterion, "
                    f"got {type(c).__name__}"
                )
        key = (action_type, entity_type)
        self._patterns.setdefault(key, []).extend(criteria)

    def lookup(
        self,
        *,
        action_type: str,
        entity_type: str | None = None,
    ) -> list[Criterion]:
        return list(
            self._patterns.get((action_type, entity_type), [])
        )

    def clear(self) -> None:
        self._patterns.clear()

    def keys(self) -> list[tuple[str, str | None]]:
        return list(self._patterns.keys())

    def __len__(self) -> int:
        return sum(len(v) for v in self._patterns.values())


class DomainPatternSource:
    """Pulls canonical criteria from a :class:`PatternRegistry`.

    Two instances are typically wired side-by-side — one with
    ``lookup_mode=MODE_TUPLE`` (specific) and one with
    ``MODE_ACTION_ONLY`` (general). Each writes its own provenance
    bucket, so the lineage shows precisely which lookup contributed
    which criterion.

    Instance-level ``name`` (``domain_pattern:tuple`` or
    ``domain_pattern:action_only``) is what the engine reads. The
    class-level ``name = "domain_pattern"`` remains the canonical
    identifier for protocol/stub tests that call ``cls.name``.
    """

    MODE_TUPLE = "tuple"
    MODE_ACTION_ONLY = "action_only"
    _MODES = frozenset({MODE_TUPLE, MODE_ACTION_ONLY})

    name = "domain_pattern"

    def __init__(
        self,
        registry: PatternRegistry | None = None,
        *,
        settings: DomainPatternSettings | None = None,
        lookup_mode: str | None = None,
    ) -> None:
        self.registry = registry
        self.settings = settings or DomainPatternSettings()
        if lookup_mode is not None and lookup_mode not in self._MODES:
            raise ValueError(
                f"unknown lookup_mode {lookup_mode!r}; "
                f"expected one of {sorted(self._MODES)} or None"
            )
        self.lookup_mode = lookup_mode
        # Instance-level name reflects the lookup mode so the engine
        # routes provenance to the right bucket. The class-level
        # ``name = "domain_pattern"`` is preserved for stub tests.
        if lookup_mode is None:
            self.name = "domain_pattern"
        else:
            self.name = f"domain_pattern:{lookup_mode}"

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        if self.registry is None:
            return SourceContribution(source_name=self.name)

        action_type = context.get(CONTEXT_KEY_ACTION_TYPE)
        if not action_type:
            return SourceContribution(source_name=self.name)

        entity_type = context.get(CONTEXT_KEY_ENTITY_TYPE)

        if self.lookup_mode == self.MODE_TUPLE:
            if not entity_type:
                return SourceContribution(source_name=self.name)
            patterns = self.registry.lookup(
                action_type=action_type, entity_type=entity_type
            )
            evidence_key = "entity_type"
            evidence_val: Any = entity_type
        elif self.lookup_mode == self.MODE_ACTION_ONLY:
            patterns = self.registry.lookup(
                action_type=action_type, entity_type=None
            )
            evidence_key = "entity_type"
            evidence_val = None
        else:
            # lookup_mode is None: merge both modes into a single bucket.
            tuple_hits = (
                self.registry.lookup(
                    action_type=action_type, entity_type=entity_type
                )
                if entity_type
                else []
            )
            action_only_hits = self.registry.lookup(
                action_type=action_type, entity_type=None
            )
            patterns = _dedup_by_name(tuple_hits + action_only_hits)
            evidence_key = "modes"
            evidence_val = ["tuple", "action_only"]

        existing = {c.name for c in current.criteria}
        criteria = _filter_new(patterns, existing)

        if not criteria:
            return SourceContribution(
                source_name=self.name,
                evidence={
                    "action_type": action_type,
                    evidence_key: evidence_val,
                    "patterns_found": 0,
                },
            )

        delta = min(
            len(criteria) * self.settings.confidence_per_pattern,
            self.settings.max_confidence_delta,
        )
        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=delta,
            evidence={
                "action_type": action_type,
                evidence_key: evidence_val,
                "patterns_found": len(criteria),
                "criterion_names": [c.name for c in criteria],
            },
        )


def _filter_new(
    patterns: list[Criterion], existing: set[str]
) -> list[Criterion]:
    """Drop patterns whose name already exists upstream."""
    seen: set[str] = set()
    out: list[Criterion] = []
    for c in patterns:
        if c.name in existing or c.name in seen:
            continue
        seen.add(c.name)
        out.append(replace(c))
    return out


def _dedup_by_name(patterns: list[Criterion]) -> list[Criterion]:
    seen: set[str] = set()
    out: list[Criterion] = []
    for c in patterns:
        if c.name in seen:
            continue
        seen.add(c.name)
        out.append(c)
    return out
