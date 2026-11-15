"""The seam where a language model would plug in.

The only shipped implementation is :class:`pda_api.providers.mock.MockProvider`,
which is deterministic, rule based and makes no network calls. A real provider
would implement the same method; everything numeric downstream (scores,
forecasts, suggestions) is computed by code from the benchmark dataset and never
by a provider.
"""

from __future__ import annotations

from typing import Protocol

from pda_api.schemas import ProtocolDesign


class LLMProvider(Protocol):
    name: str

    def extract_design(self, text: str) -> ProtocolDesign:
        """Extract the structured trial design from the protocol text."""
        ...


def get_provider(name: str) -> LLMProvider:
    if name == "mock":
        from pda_api.providers.mock import MockProvider

        return MockProvider()
    raise ValueError(f"Unknown LLM provider '{name}'. Only 'mock' is shipped.")
