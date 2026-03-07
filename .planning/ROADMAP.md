# Roadmap: Contract Negotiator Plugin -- v2.0 GitHub Release

## Overview

Audit every file in the packaged plugin for correctness and currency, produce accurate documentation, then push a clean release to GitHub. Phase 30 handles all audit, documentation, and sync work. Phase 31 handles the actual GitHub release.

## Milestones

- v1.x Initial Plugin Packaging -- Phases 1-29 (completed in ~/Claude-Plugin)
- v2.0 GitHub Release Preparation -- Phases 30-31 (this milestone)

## Phases

**Phase Numbering:**
- Continues from v1.x (last phase: 29)
- Integer phases (30, 31): Planned milestone work
- Decimal phases (30.1, 30.2): Urgent insertions if needed

- [ ] **Phase 30: Codebase Audit and Documentation Review** - Remove stale files, fix discrepancies, sync sources, and produce accurate documentation
- [ ] **Phase 31: Prepare and Push to GitHub** - Set remote, commit clean state, push to sarturko-maker/Claude-Plugin-MCP

## Phase Details

### Phase 30: Codebase Audit and Documentation Review
**Goal**: Every file in the repo is correct, current, safe to publish, and accurately documented
**Depends on**: Nothing (first phase of v2.0; builds on v1.x phases 1-29)
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04, AUD-05, AUD-06, AUD-07, AUD-08, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, SYN-01, SYN-02
**Success Criteria** (what must be TRUE):
  1. No stale or orphaned files exist in the repo (claude-v-claude/ removed, no test debris)
  2. All configuration files (plugin.json, .gitignore, .mcp.json, start-mcp.sh) contain correct values with no secrets or unnecessary hardcoded paths
  3. README.md accurately describes the plugin's capabilities, install steps, and usage -- every claim verified against actual code
  4. DISCLAIMER.md, SECURITY.md, CONTRIBUTING.md, and PRIVACY.md exist with correct content and links pointing to Claude-Plugin-MCP
  5. Source files (yolo-negotiation command, defaults/) are synced back to ~/Claude-Plugin so both repos match
**Plans:** 3 plans

Plans:
- [ ] 30-01-PLAN.md -- Cleanup stale files, bundle MCP server source, fix all configuration
- [ ] 30-02-PLAN.md -- Update all documentation (README, SECURITY, CONTRIBUTING, PRIVACY, DISCLAIMER)
- [ ] 30-03-PLAN.md -- Sync commands/defaults to source repo and verify SKILL.md

### Phase 31: Prepare and Push to GitHub
**Goal**: The plugin is live on GitHub at sarturko-maker/Claude-Plugin-MCP with a clean, professional appearance
**Depends on**: Phase 30
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. Git remote points to https://github.com/sarturko-maker/Claude-Plugin-MCP
  2. A clean commit with descriptive message is pushed to the main branch
  3. README renders correctly on GitHub and the repository structure looks clean to a visitor
**Plans**: TBD

Plans:
- [ ] 31-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 30 -> 31

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 30. Codebase Audit and Documentation Review | v2.0 | 0/3 | Not started | - |
| 31. Prepare and Push to GitHub | v2.0 | 0/1 | Not started | - |
