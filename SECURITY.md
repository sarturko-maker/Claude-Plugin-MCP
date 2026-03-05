# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.4.x   | Yes       |
| < 1.4   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **For security vulnerabilities:** Email the maintainer directly (see the repository's GitHub profile for contact information). Please do NOT open public GitHub issues for security vulnerabilities.
2. **For non-sensitive issues:** Open a GitHub issue with the "security" label.
3. **Response time:** We aim to acknowledge reports within 72 hours and provide a fix timeline within one week.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

## Security Model

This is a **local developer tool**, not a web service. The threat model reflects this scope:

- **Deployment:** Runs locally on the user's machine as a Claude Desktop plugin
- **Communication:** MCP server communicates only with Claude via stdio transport or localhost-bound SSE (127.0.0.1)
- **Data handling:** Processes legally privileged documents entirely in-memory
- **Persistence:** No data persistence between invocations -- stateless by design
- **Network:** No outbound network calls from the processing pipeline
- **Authentication:** No user authentication (local tool, single user)
- **Document processing:** All OOXML manipulation via lxml and python-docx with safe defaults

### Trust Boundaries

```
Claude Desktop  <--stdio/localhost SSE-->  MCP Server  -->  Local filesystem (.docx files)
                                               |
                                           adeu engine (in-process, no network)
```

The MCP server trusts Claude to provide valid parameters (Pydantic validates all inputs). The server does NOT trust file paths -- all paths are validated for traversal attacks and correct extensions before use.

## MCP Tool Annotations

All 9 registered MCP tools have `ToolAnnotations` declaring their behavior hints for Claude Desktop and directory compliance:

| Tool | File | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|------|------|:------------:|:---------------:|:--------------:|:-------------:|
| Ingest Document | ingest_tools.py | true | - | - | false |
| Get State of Play | ingest_tools.py | true | - | - | false |
| Accept Changes | action_tools.py | false | true | false | false |
| Counter-Propose Changes | action_tools.py | false | true | false | false |
| Add Comments | action_tools.py | false | true | false | false |
| Reply to Comments | action_tools.py | false | true | false | false |
| Resolve Comments | action_tools.py | false | true | false | false |
| Execute Pipeline | pipeline_tool.py | false | true | false | false |
| Redline Document | redline_tool.py | false | true | false | false |

- `openWorldHint=false` on all tools: they operate only on local .docx files, never make external requests.
- `idempotentHint=false` on write tools: running the same edits twice produces duplicate tracked changes.
- Read-only tools omit `destructiveHint` and `idempotentHint` (default false/not applicable).

## Audit Findings

Full security audit conducted 2026-03-05 using automated code scanning and manual review.

### Finding 1: Missing MCP Tool Annotations

- **Severity:** HIGH (Anthropic directory rejection risk)
- **Status:** Fixed
- **Description:** None of the 9 MCP tools had `ToolAnnotations` declaring `readOnlyHint` or `destructiveHint`. This is the #1 rejection reason for Anthropic directory submissions.
- **Disposition:** Added `ToolAnnotations` to all 9 tools with correct hints (Phase 21, Plan 01). Covered by 51 parametrized tests.

### Finding 2: SSE Server Bound to 0.0.0.0

- **Severity:** MEDIUM
- **Status:** Fixed
- **Description:** `src/mcp_server/__main__.py` bound the SSE transport server to `0.0.0.0`, making it accessible from any network interface. For a local developer tool, this unnecessarily exposes the MCP server.
- **Disposition:** Changed to `127.0.0.1` for localhost-only access (Phase 21, Plan 01). Verified by source-level test.

### Finding 3: Config Writer Missing Path Traversal Validation

- **Severity:** LOW-MEDIUM
- **Status:** Fixed
- **Description:** `src/config/writer.py` functions `write_global_config` and `write_project_config` did not validate the `project_dir` parameter for path traversal (`..`). A crafted path could write config files to arbitrary locations.
- **Disposition:** Added `_has_path_traversal` check matching the pattern in `ingestion/validation.py` (Phase 21, Plan 01). Covered by functional test.

### Finding 4: Output Validator Path Leak in Warnings

- **Severity:** LOW
- **Status:** Fixed
- **Description:** `src/validation/output_validator.py` included full file paths in ZIP validation warning messages, potentially exposing internal directory structure.
- **Disposition:** Changed to use `Path.name` for filename-only warnings (Phase 21, Plan 01). Covered by test.

### Finding 5: Exception Message Path Leakage in MCP Tools

- **Severity:** MEDIUM
- **Status:** Fixed
- **Description:** All 9 MCP tool exception handlers used `f"Error ...: {error}"`, passing raw exception messages to the client. Exceptions from lxml, python-docx, and adeu may include full filesystem paths in their string representation, leaking internal directory structure.
- **Disposition:** Created `src/mcp_server/error_sanitizer.py` with regex-based path stripping. Updated all 9 exception handlers to use `sanitize_error_message()` (Phase 21, Plan 02). Covered by 9 tests.

### Finding 6: Malicious .docx Processing (XXE/Zip Bombs)

- **Severity:** LOW (Accepted Risk)
- **Status:** Known Issue
- **Description:** Investigated whether crafted .docx files could exploit the pipeline via XML entity expansion (XXE), zip bombs, or circular references.
- **Investigation results:**
  - lxml's default `XMLParser` disables DTD loading and entity expansion -- safe against XXE.
  - Neither the plugin code nor adeu override lxml's safe defaults (no custom `XMLParser` configuration found).
  - python-docx uses lxml defaults for all XML parsing.
  - Zip bomb protection depends on the OS/python zipfile module -- no explicit size checks on extracted XML parts.
- **Disposition:** Accepted risk. The tool processes documents from the user's own filesystem, not from untrusted network sources. lxml defaults provide adequate XXE protection. Zip bomb risk is mitigated by the local-only deployment model.

### Finding 7: Adeu Engine Isolation

- **Severity:** INFORMATIONAL
- **Status:** Verified Secure
- **Description:** Audited the adeu engine source for network calls, environment variable access, and filesystem side effects.
- **Investigation results:**
  - No network-related imports (`requests`, `urllib`, `httpx`, `socket`, `http.client`) in adeu source code.
  - One `os.environ.get("APPDATA")` in `adeu/cli.py` -- CLI configuration path lookup only, not called by the plugin.
  - No `subprocess`, `os.system`, or other process spawning.
  - Adeu operates purely on in-memory lxml trees and python-docx Document objects.
- **Disposition:** Adeu is appropriately isolated. No network access, no sensitive environment variable reads from the plugin's usage path.

### Finding 8: No File Size Limits on .docx Input

- **Severity:** LOW (Accepted Risk)
- **Status:** Known Issue
- **Description:** `validate_docx_path()` checks file existence and extension but does not enforce a size limit. The config loader has a 1MB limit, but document ingestion has no limit. A multi-GB document could cause memory exhaustion.
- **Disposition:** Accepted risk. MCP tools are called by Claude, not by untrusted users. Claude selects files from the user's own filesystem. The user would know if they're processing an abnormally large document. Adding a size limit would risk rejecting legitimate large contracts.

### Finding 9: Temporary File Cleanup

- **Severity:** INFORMATIONAL
- **Status:** Verified Secure
- **Description:** Investigated whether the pipeline executor properly cleans up temporary files containing sensitive document data on all code paths.
- **Investigation results:**
  - `src/pipeline/orchestrator.py` uses `with tempfile.TemporaryDirectory() as tmp_dir:` -- a context manager that guarantees cleanup even on exceptions.
  - All temp file operations happen within this context manager scope.
  - No temp files are created outside the managed directory.
- **Disposition:** Secure. The context manager pattern ensures cleanup on all code paths including errors.

### Finding 10: Automated Code Scan Results

- **Severity:** INFORMATIONAL
- **Status:** Verified Secure
- **Description:** Full automated scan of all Python source in `src/` for unsafe patterns.
- **Results:**
  - No `eval()`, `exec()`, `pickle`, `subprocess`, `yaml.load`, `__import__`, or `os.system` usage.
  - No network-related imports (`requests`, `urllib`, `httpx`, `socket`).
  - No `os.environ` or `os.getenv` access.
  - No hardcoded secrets, API keys, tokens, or passwords.
  - All `etree.fromstring()` calls use lxml safe defaults (no custom parser configuration).
- **Disposition:** Clean. No unsafe patterns detected.

## Already Secure

These security controls were already in place before the Phase 21 audit:

| Control | Implementation | Evidence |
|---------|---------------|----------|
| Path traversal on input paths | `validate_docx_path()` checks `..` in all raw path parts | `src/ingestion/validation.py` |
| Path traversal on output paths | `validate_output_path()` checks `..` in all raw path parts | `src/pipeline/orchestrator.py` |
| Extension validation | Both input and output require `.docx` extension | `src/ingestion/validation.py`, `src/pipeline/orchestrator.py` |
| Input validation | Pydantic models validate all MCP tool parameters | All tool files use typed parameters |
| No unsafe deserialization | Zero instances of pickle, eval, exec, subprocess | Verified by automated scan |
| No hardcoded credentials | Zero instances found | Verified by automated scan |
| Config file size limit | Config loader enforces 1MB maximum | `src/config/loader.py` |
| Config path traversal | Config loader validates paths | `src/config/loader.py` |
| Stateless operation | No database, no session storage, no persistent state | Architecture by design |
| Error messages use filename only | Validation errors use `path.name` not full paths | `src/ingestion/validation.py` |

## Dependencies

All external dependencies reviewed for known vulnerabilities as of 2026-03-05:

| Package | Version | Purpose | CVE Status |
|---------|---------|---------|------------|
| adeu | 0.7.0 | OOXML redlining engine | No known CVEs (private package) |
| lxml | 6.0.2 | XML parsing for OOXML | No direct CVEs in 6.0.2; underlying libxml2 had CVE-2025-32414 (fixed in libxml2 2.13.8+) |
| python-docx | 1.2.0 | .docx file manipulation | No known CVEs |
| mcp | 1.25.0 | MCP server SDK | No known CVEs |
| pydantic | 2.12.5 | Input validation models | No known CVEs |
| starlette | 0.51.0 | ASGI framework for SSE | CVE-2025-62727 and CVE-2025-54121 both patched in this version |
| uvicorn | 0.40.0 | ASGI server | No known CVEs |
| diff-match-patch | 20241021 | Word-level diffing | No known CVEs |
| structlog | 25.5.0 | Structured logging (adeu dep) | No known CVEs |

**Supply chain summary:** All dependencies are well-maintained open-source packages with no unpatched CVEs. The starlette CVEs (DoS via Range headers and multipart parsing) are patched in the installed version 0.51.0.

## Responsible Disclosure

We follow a responsible disclosure process:

1. **Report:** Send vulnerability details to the maintainer (see GitHub profile for contact).
2. **Acknowledge:** We will acknowledge receipt within 72 hours.
3. **Assess:** We will assess severity and provide a fix timeline within one week.
4. **Fix:** Security fixes are prioritized and released as patch versions.
5. **Disclose:** After the fix is released, findings may be disclosed publicly.

We ask that reporters:
- Allow reasonable time for a fix before public disclosure
- Avoid exploiting vulnerabilities beyond what is necessary to demonstrate the issue
- Do not access or modify other users' data

---

*Security audit conducted: 2026-03-05*
*Last updated: 2026-03-05*
