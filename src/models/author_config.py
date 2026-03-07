"""Client author configuration for tracked change attribution.

Centralizes the author identity used when applying negotiation operations
(accept, counter-propose, comment, reply, resolve). Replaces the bare
`client_author` string with a rich config that includes date override,
initials, and timestamp generation.

Usage:
    from src.models.author_config import AuthorConfig

    config = AuthorConfig(name="Blackwood Partners LLP")
    config.initials   # "BPL"
    config.timestamp  # "2026-02-28T01:03:00Z" (current UTC)

    config = AuthorConfig(
        name="Blackwood Partners LLP",
        date_override=date(2026, 2, 15),
        initials_override="BP",
    )
    config.initials   # "BP"
    config.timestamp  # "2026-02-15T00:00:00Z"
"""

from datetime import date

from pydantic import BaseModel, computed_field


class AuthorConfig(BaseModel):
    """Client author configuration for tracked change attribution.

    Attributes:
        name: Full author name used in w:author attributes.
        date_override: Fixed date for timestamp generation. If None, uses
            current UTC time. Useful for deterministic test output.
        initials_override: Explicit initials string. If None, initials
            are auto-generated from the first letter of each word in name.
    """

    name: str
    date_override: date | None = None
    initials_override: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def initials(self) -> str:
        """Return author initials (override or auto-generated from name)."""
        if self.initials_override:
            return self.initials_override
        return "".join(word[0].upper() for word in self.name.split() if word)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def timestamp(self) -> str:
        """Return ISO 8601 UTC timestamp for tracked change w:date attributes."""
        # Deferred import to avoid circular dependency:
        # models.__init__ -> author_config -> negotiation.timestamp
        # -> negotiation.__init__ -> accept_changes -> ingestion -> models
        from src.negotiation.timestamp import generate_timestamp

        return generate_timestamp(self.date_override)
