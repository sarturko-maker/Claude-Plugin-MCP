"""Three-level fallback chain for config file discovery and loading.

The loader finds and reads markdown config files from three locations in
priority order: explicit paths, project directory, global config directory.
If no files are found at any level, shipped defaults are used. The loader
never raises on missing files -- it always returns usable configuration.

This module has ZERO imports from other src/ packages to prevent circular
imports. It only uses stdlib + Pydantic + its sibling config modules.
"""

from pathlib import Path

from src.config.defaults import (
    DEFAULT_AUTHORITY,
    DEFAULT_PERSONA,
    DEFAULT_PLAYBOOK_TEMPLATE,
)
from src.config.models import NegotiationConfig

GLOBAL_CONFIG_DIR = Path.home() / ".config" / "claude-negotiator"

_MAX_CONFIG_FILE_SIZE = 1_000_000  # 1 MB limit to prevent memory exhaustion


def load_config(
    project_dir: str | None = None,
    persona_path: str | None = None,
    authority_path: str | None = None,
    playbook_path: str | None = None,
) -> NegotiationConfig:
    """Load negotiation config from the three-level fallback chain.

    Explicit paths override convention-based discovery. Project dir overrides
    global dir. Global dir overrides shipped defaults. Never raises on missing
    files -- always returns usable configuration.

    Args:
        project_dir: Project directory to search for config files.
        persona_path: Explicit path to a persona config file.
        authority_path: Explicit path to an authority config file.
        playbook_path: Explicit path to a playbook file.

    Returns:
        NegotiationConfig with loaded or default content.
    """
    persona = _load_layer("PERSONA.md", project_dir, persona_path, DEFAULT_PERSONA)
    authority = _load_layer(
        "AUTHORITY.md", project_dir, authority_path, DEFAULT_AUTHORITY
    )
    playbook = _load_playbook(project_dir, playbook_path)
    has_custom = _has_custom_config(project_dir)

    return NegotiationConfig(
        persona=persona,
        authority=authority,
        playbook=playbook,
        has_custom_config=has_custom,
    )


def _load_layer(
    filename: str,
    project_dir: str | None,
    explicit_path: str | None,
    default_content: str,
) -> str:
    """Load a single config layer with three-level fallback.

    Priority: explicit_path > project_dir/filename > global_dir/filename > default.
    Explicit paths are validated against path traversal before reading.

    Args:
        filename: Config filename to search for (e.g. "PERSONA.md").
        project_dir: Project directory path, or None.
        explicit_path: User-provided explicit file path, or None.
        default_content: Shipped default content to use as final fallback.

    Returns:
        The loaded config content, or default_content if nothing was found.
    """
    if explicit_path is not None:
        if _has_path_traversal(explicit_path):
            return default_content
        return _read_file_safe(explicit_path, default_content)

    if project_dir is not None:
        project_path = Path(project_dir) / filename
        if project_path.is_file():
            return _read_file_safe(str(project_path), default_content)

    global_path = GLOBAL_CONFIG_DIR / filename
    if global_path.is_file():
        return _read_file_safe(str(global_path), default_content)

    return default_content


def _load_playbook(
    project_dir: str | None,
    explicit_path: str | None,
) -> str:
    """Load a playbook file from explicit path or project directory discovery.

    Playbooks are per-matter and do not fall back to global config. If no
    playbook is found, returns an empty string. When multiple PLAYBOOK-*.md
    files exist in the project directory, the first alphabetically is used.

    Args:
        project_dir: Project directory to search for playbook files.
        explicit_path: User-provided explicit playbook path, or None.

    Returns:
        Playbook content, or empty string if none found.
    """
    if explicit_path is not None:
        if _has_path_traversal(explicit_path):
            return ""
        return _read_file_safe(explicit_path, "")

    if project_dir is not None:
        project_path = Path(project_dir)
        playbook_files = sorted(project_path.glob("PLAYBOOK-*.md"))
        if playbook_files:
            return _read_file_safe(str(playbook_files[0]), "")

    return ""


def _read_file_safe(file_path: str, default: str) -> str:
    """Read a file with UTF-8 encoding, returning default on any error.

    Returns the default value if the file does not exist, cannot be read,
    has encoding errors, exceeds the size limit, or contains only whitespace.

    Args:
        file_path: Absolute or relative path to the file.
        default: Value to return if the file cannot be read.

    Returns:
        The file content as a string, or default on any error.
    """
    try:
        path = Path(file_path)
        if not path.is_file():
            return default
        if path.stat().st_size > _MAX_CONFIG_FILE_SIZE:
            return default
        content = path.read_text(encoding="utf-8")
        return content if content.strip() else default
    except (OSError, UnicodeDecodeError):
        return default


def _has_custom_config(project_dir: str | None) -> bool:
    """Check whether any custom config files exist beyond shipped defaults.

    Returns True if PERSONA.md or AUTHORITY.md exists in either the project
    directory or the global config directory. Used to determine whether to
    trigger the conversational setup flow.

    Args:
        project_dir: Project directory path, or None.

    Returns:
        True if custom config files were found.
    """
    if project_dir is not None:
        project_path = Path(project_dir)
        if (project_path / "PERSONA.md").is_file():
            return True
        if (project_path / "AUTHORITY.md").is_file():
            return True

    if (GLOBAL_CONFIG_DIR / "PERSONA.md").is_file():
        return True
    if (GLOBAL_CONFIG_DIR / "AUTHORITY.md").is_file():
        return True

    return False


def _has_path_traversal(file_path: str) -> bool:
    """Check if a file path contains directory traversal components.

    Rejects paths containing '..' in any component to prevent traversal
    attacks. Same pattern used in Phase 3's path validation.

    Args:
        file_path: The path string to validate.

    Returns:
        True if the path contains traversal components (should be rejected).
    """
    path = Path(file_path)
    return ".." in path.parts
