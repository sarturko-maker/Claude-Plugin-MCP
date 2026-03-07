"""Config package for negotiation plugin configuration.

Provides config file discovery, loading, and writing. The config system
uses a three-level fallback chain: project directory, global config
directory (~/.config/claude-negotiator/), and shipped defaults. It never
fails -- if no config files exist, sensible defaults are used.

Public API:
    load_config: Load config from the fallback chain.
    write_global_config: Save config to the global directory.
    write_project_config: Save config to a project directory.
    NegotiationConfig: Pydantic model holding loaded config.
    SETUP_PROMPT: Instructions for the conversational setup flow.
    DEFAULT_PERSONA: Default persona markdown content.
    DEFAULT_AUTHORITY: Default authority framework markdown content.
    DEFAULT_PLAYBOOK_TEMPLATE: Default playbook template markdown content.
"""

from src.config.defaults import (
    DEFAULT_AUTHORITY,
    DEFAULT_PERSONA,
    DEFAULT_PLAYBOOK_TEMPLATE,
    SETUP_PROMPT,
)
from src.config.loader import load_config
from src.config.models import NegotiationConfig
from src.config.writer import write_global_config, write_project_config

__all__ = [
    "load_config",
    "write_global_config",
    "write_project_config",
    "NegotiationConfig",
    "SETUP_PROMPT",
    "DEFAULT_PERSONA",
    "DEFAULT_AUTHORITY",
    "DEFAULT_PLAYBOOK_TEMPLATE",
]
