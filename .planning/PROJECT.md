# Contract Negotiator -- Claude Plugin (Packaged)

## What This Is

The distribution-ready package of the Contract Negotiator Claude plugin. Contains skills, commands, defaults, MCP configuration, and documentation for end users. Source code lives in ~/Claude-Plugin; this repo is the clean, publishable artifact that goes to GitHub.

## Core Value

Every file in this repo must be correct, current, and safe to publish. No stale artifacts, no hardcoded paths, no secrets, no test debris.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet -- this is the first milestone for this repo)

### Active

<!-- Current scope. Building toward these. -->

- [ ] All skills and defaults match latest source (Phase 29+)
- [ ] Documentation is accurate and cross-checked against reality
- [ ] No stale or orphaned files
- [ ] No secrets, hardcoded paths, or personal data
- [ ] Clean GitHub release at sarturko-maker/Claude-Plugin-MCP

### Out of Scope

- Source code changes (that happens in ~/Claude-Plugin)
- New features or capabilities
- CI/CD pipeline setup

## Current Milestone: v2.0 GitHub Release Preparation

**Goal:** Audit every file, fix all issues, create accurate documentation, and push a clean release to GitHub.

**Target features:**
- Codebase audit removing stale files and fixing discrepancies
- Complete documentation suite (README, DISCLAIMER, LICENSE, SECURITY, .gitignore)
- Clean initial push to sarturko-maker/Claude-Plugin-MCP

## Context

- Plugin version: 1.8.0 (per plugin.json)
- Source repo: ~/Claude-Plugin (not published here)
- Target repo: https://github.com/sarturko-maker/Claude-Plugin-MCP
- MCP server runs from source repo via start-mcp.sh
- Built on Adeu OOXML redlining engine
- 11 MCP tools registered in the server

## Constraints

- **No source code:** This repo contains only the plugin package, not the Python source
- **Local paths:** start-mcp.sh necessarily has local paths -- must be documented
- **Dependencies:** Users need Python 3.11+, adeu, python-docx, lxml, pydantic

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate repo for packaged plugin | Keep source (tests, .planning, GSD) separate from distribution | -- Pending |
| MIT License | Standard open-source license for POC | -- Pending |

---
*Last updated: 2026-03-07 after milestone v2.0 started*
