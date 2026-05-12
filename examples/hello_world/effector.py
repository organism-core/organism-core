"""Hello-world effector — the simplest possible side-effect tool.

Returns a greeting dict for a given name. Includes the fields the
DoD validates against (``greeting`` itself, plus ``mentions_name``,
``length``, and a ``friendly_tone`` self-attestation that the
LLM-judge mode overrides when configured)."""

from __future__ import annotations

from typing import Any

from organism.adapter import BaseEffector


class HelloGreeter(BaseEffector):
    name = "hello_greeter"

    def __init__(self, *, attest_friendly: bool = True) -> None:
        # When the demo runs without an LLM judge, the effector
        # self-attests friendliness deterministically. When the LLM
        # judge is configured, this flag is irrelevant — the judge
        # decides instead. Concrete consumers would never self-attest
        # qualitative criteria; the demo does it only to stay green
        # without an API key.
        self.attest_friendly = attest_friendly

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        # Empty: the DoD engine reads the entity frontmatter and the
        # demo passes evaluator hints through that frontmatter.
        return {}

    def act(self, request: Any) -> Any:
        name = str(request).strip() or "World"
        greeting = f"Hello, {name}! Welcome to organism-core."
        return {
            "greeting": greeting,
            "mentions_name": name in greeting,
            "length": len(greeting),
            # Only consumed when the criterion uses evaluator=self_check.
            # In llm_judge mode the judge sees ``greeting`` directly.
            "friendly_tone": self.attest_friendly,
        }
