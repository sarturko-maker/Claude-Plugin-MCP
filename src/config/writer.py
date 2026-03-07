"""Config file writer for saving generated configuration to disk.

Provides functions to write persona and authority config files to either
the global config directory (~/.config/claude-negotiator/) or a project
directory. Used after the conversational setup flow generates config content,
or when a user wants project-level overrides.
"""

from pathlib import Path

from src.config.loader import GLOBAL_CONFIG_DIR


def write_global_config(persona: str, authority: str) -> Path:
    """Write persona and authority config to the global config directory.

    Creates ~/.config/claude-negotiator/ if it does not exist. Overwrites
    any existing files. Both files are written with UTF-8 encoding.

    Args:
        persona: Persona markdown content to write to PERSONA.md.
        authority: Authority framework markdown content to write to
            AUTHORITY.md.

    Returns:
        Path to the global config directory.
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (GLOBAL_CONFIG_DIR / "PERSONA.md").write_text(persona, encoding="utf-8")
    (GLOBAL_CONFIG_DIR / "AUTHORITY.md").write_text(authority, encoding="utf-8")
    return GLOBAL_CONFIG_DIR


def write_project_config(
    project_dir: str,
    persona: str | None = None,
    authority: str | None = None,
    playbook: str | None = None,
) -> Path:
    """Write config files to a project directory.

    Only writes files for non-None arguments. This allows selective
    creation of project-level overrides without affecting other config
    files. The project directory must already exist.

    Args:
        project_dir: Path to the project directory.
        persona: Persona markdown content, or None to skip.
        authority: Authority framework markdown content, or None to skip.
        playbook: Playbook markdown content, or None to skip.

    Returns:
        Path to the project directory.
    """
    project_path = Path(project_dir)

    if ".." in project_path.parts:
        raise ValueError("Invalid project directory path")

    if persona is not None:
        (project_path / "PERSONA.md").write_text(persona, encoding="utf-8")

    if authority is not None:
        (project_path / "AUTHORITY.md").write_text(authority, encoding="utf-8")

    if playbook is not None:
        (project_path / "PLAYBOOK-custom.md").write_text(playbook, encoding="utf-8")

    return project_path
