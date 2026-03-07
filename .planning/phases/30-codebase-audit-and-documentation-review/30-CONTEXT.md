# Phase 30: Codebase Audit and Documentation Review - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit every file in ~/Claude-Plugin-Packaged for correctness and currency. Remove stale artifacts, fix discrepancies, update documentation, bundle the MCP server source for self-contained install, and sync commands/defaults back to the source repo. No new features -- this is cleanup and documentation only.

</domain>

<decisions>
## Implementation Decisions

### MCP Server Bundling
- Copy src/ (78 Python files) from ~/Claude-Plugin into this repo
- Add pyproject.toml with pip-installable package
- Adeu dependency: git dependency pointing to https://github.com/dealfluence/adeu.git@v0.7.0 (not PyPI -- only v0.0.1 placeholder on PyPI, we need v0.7.0)
- Other dependencies (python-docx, lxml, pydantic, mcp, etc.) from PyPI as normal
- Python minimum version: 3.11+ (enforced by Adeu's python_requires >=3.11; MCP requires >=3.10)

### start-mcp.sh Strategy
- Auto-detect: script finds the source relative to its own location (since src/ is now bundled, it's in the same repo)
- Python version check at script start with clear error message if < 3.11
- Use `python3` as the command (not hardcoded /usr/bin/python)
- .mcp.json keeps `${CLAUDE_PLUGIN_ROOT}/scripts/start-mcp.sh` (resolved by Claude Code's plugin system)

### README Structure
- Quick start code block first (git clone, pip install, claude --plugin-dir)
- Detailed step-by-step below for those who need it
- Cowork instructions: skip for now
- Prerequisites: Python 3.11+, pip, git, Claude Code -- one line each, verified against actual requirements
- /negotiate is the primary command; /yolo-negotiation mentioned as variant for experienced users
- Every claim in README must be cross-checked against actual code

### Repo Link Strategy
- All issues and PRs directed to Claude-Plugin-MCP (the public-facing repo)
- plugin.json repository field: https://github.com/sarturko-maker/Claude-Plugin-MCP
- CONTRIBUTING.md, PRIVACY.md, SECURITY.md: all links point to Claude-Plugin-MCP
- SECURITY.md supported versions: 2.0.x (this release)
- SECURITY.md tool count: 11 (verified -- 2 ingest + 5 action + 1 pipeline + 1 redline + 2 styler)
- SECURITY.md ToolAnnotations table: keep source file references (they'll be valid once src/ is bundled)

### Source Sync Scope
- Sync back to ~/Claude-Plugin: commands/yolo-negotiation/ and defaults/ directory only
- No doc sync back -- docs live separately in each repo
- Source repo (~/Claude-Plugin) remains the canonical development repo

### Stale File Removal
- Remove: claude-v-claude/ directory (4 test docx files)
- Remove: .claude/settings.local.json (GSD permissions -- not for distribution)
- .gitignore: add .planning/, .venv/, __pycache__/, *.pyc, output/

### Claude's Discretion
- pyproject.toml package name and structure details
- Exact auto-detect logic in start-mcp.sh
- Order of operations within the phase (bundling vs docs vs cleanup)
- Whether to update plugin.json version to 2.0.0 or keep 1.8.0

</decisions>

<specifics>
## Specific Ideas

- Python version requirement must be derived from actual dependency metadata, not guessed
- Adeu's upstream repo (dealfluence/adeu) has the v0.7.0 tag -- use that for the git dependency
- 11 MCP tools confirmed by counting @mcp.tool decorators in source (excluding __init__.py comment)
- README usage examples already exist and are good -- keep them, just fix the install section

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- src/ tree (78 Python files): Full MCP server + negotiation pipeline, ready to copy
- samples/ directory: clean and redlined test documents, confirmed for inclusion
- defaults/ directory: PERSONA.md, AUTHORITY.md, PLAYBOOK-template.md already written

### Established Patterns
- MCP server entry point: python -m src.mcp_server
- Plugin structure: .claude-plugin/plugin.json + .mcp.json + skills/ + commands/
- Three-level config fallback: project dir > ~/.config/claude-negotiator/ > shipped defaults

### Integration Points
- start-mcp.sh: bridge between Claude Code plugin system and Python MCP server
- .mcp.json: plugin system reads this to find and start the MCP server
- pyproject.toml: new file that makes the repo pip-installable

### Known Issues to Fix
1. plugin.json: missing privacy_policy field, wrong repository URL
2. start-mcp.sh: hardcoded paths to /home/sarturko/...
3. SECURITY.md: says 9 tools (should be 11), supported versions 1.4.x (should be 2.0.x)
4. CONTRIBUTING.md + PRIVACY.md: link to source repo, should link to Claude-Plugin-MCP
5. .gitignore: missing .planning/ exclusion
6. claude-v-claude/: stale test files
7. .claude/settings.local.json: GSD permissions leaked into distribution

</code_context>

<deferred>
## Deferred Ideas

- CI to validate packaged files match source (AUTO-02 in requirements -- future milestone)
- Setup script that configures paths automatically (AUTO-01 -- future milestone)
- Cowork installation instructions (skip for now -- revisit when platform is established)

</deferred>

---

*Phase: 30-codebase-audit-and-documentation-review*
*Context gathered: 2026-03-07*
