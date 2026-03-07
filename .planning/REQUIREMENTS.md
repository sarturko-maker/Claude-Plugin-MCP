# Requirements: Contract Negotiator Plugin -- v2.0 GitHub Release

**Defined:** 2026-03-07
**Core Value:** Every file must be correct, current, and safe to publish

## v2.0 Requirements

### Audit

- [ ] **AUD-01**: All stale files removed (claude-v-claude/, .claude/settings.local.json)
- [ ] **AUD-02**: plugin.json has correct version, repository URL (Claude-Plugin-MCP), and privacy_policy field
- [x] **AUD-03**: SKILL.md files match latest source (Phase 29 anchoring fix, commenting rules, validation gate, input validation)
- [ ] **AUD-04**: start-mcp.sh uses generic paths or is clearly documented as requiring user customization
- [ ] **AUD-05**: SECURITY.md reflects current tool count (11), current supported versions (1.8.x), and accurate audit findings
- [ ] **AUD-06**: CONTRIBUTING.md and PRIVACY.md link to correct repo (Claude-Plugin-MCP)
- [ ] **AUD-07**: .gitignore excludes .venv/, __pycache__/, *.pyc, output/, .planning/
- [ ] **AUD-08**: No secrets, API keys, personal data, or unnecessary hardcoded paths in any file

### Documentation

- [ ] **DOC-01**: README.md has POC disclaimer banner, accurate install instructions (claude --plugin-dir and zip upload for Cowork), architecture overview, and usage examples showing /negotiate and /yolo-negotiation
- [ ] **DOC-02**: Every claim in README cross-checked against actual code (surgical diffs, multi-round, word-level diff, tool count)
- [ ] **DOC-03**: DISCLAIMER.md covers POC status, AI-assisted development, not legal advice, not for production, all output AI-generated, must be reviewed, no liability
- [ ] **DOC-04**: SECURITY.md documents data flows, stateless processing, no document retention, and current dependency list
- [ ] **DOC-05**: .mcp.json local path documented in README with user setup instructions

### Sync

- [x] **SYN-01**: yolo-negotiation command synced back to ~/Claude-Plugin/commands/
- [x] **SYN-02**: defaults/ directory synced back to ~/Claude-Plugin/defaults/

### Release

- [ ] **REL-01**: Git remote set to https://github.com/sarturko-maker/Claude-Plugin-MCP
- [ ] **REL-02**: Clean commit with descriptive message pushed to main branch
- [ ] **REL-03**: Repo looks correct on GitHub (README renders, structure is clean)

## Future Requirements

### Automation

- **AUTO-01**: Setup script that configures start-mcp.sh paths automatically
- **AUTO-02**: CI to validate packaged files match source

## Out of Scope

| Feature | Reason |
|---------|--------|
| Source code changes | Happens in ~/Claude-Plugin, not here |
| New negotiation features | This milestone is audit and release only |
| CI/CD pipeline | Future milestone |
| Automated testing in this repo | Tests live in source repo |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUD-01 | Phase 30 | Pending |
| AUD-02 | Phase 30 | Pending |
| AUD-03 | Phase 30 | Complete |
| AUD-04 | Phase 30 | Pending |
| AUD-05 | Phase 30 | Pending |
| AUD-06 | Phase 30 | Pending |
| AUD-07 | Phase 30 | Pending |
| AUD-08 | Phase 30 | Pending |
| DOC-01 | Phase 30 | Pending |
| DOC-02 | Phase 30 | Pending |
| DOC-03 | Phase 30 | Pending |
| DOC-04 | Phase 30 | Pending |
| DOC-05 | Phase 30 | Pending |
| SYN-01 | Phase 30 | Complete |
| SYN-02 | Phase 30 | Complete |
| REL-01 | Phase 31 | Pending |
| REL-02 | Phase 31 | Pending |
| REL-03 | Phase 31 | Pending |

**Coverage:**
- v2.0 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after initial definition*
