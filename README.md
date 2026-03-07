# Contract Negotiator -- Claude Plugin

> **Proof of Concept.** This is a proof of concept for testing and evaluation by qualified legal professionals only. It is NOT production software, does not provide legal advice, and must not be used for live client matters. All output is AI-generated and must be reviewed by a qualified legal professional. See [DISCLAIMER.md](DISCLAIMER.md).

A Claude plugin that turns Claude into an agentic contract negotiation assistant. Upload a Word document -- clean or with existing tracked changes from any number of prior rounds -- give instructions, and get back a properly redlined `.docx` with layered Track Changes and correct author attribution.

Built on the [Adeu](https://github.com/dealfluence/adeu) OOXML redlining engine.

## Quick Start

```bash
git clone https://github.com/sarturko-maker/Claude-Plugin-MCP.git
cd Claude-Plugin-MCP
pip install .
claude --plugin-dir ./
```

## Prerequisites

- **Python 3.11+** (required by the Adeu dependency)
- **pip** (for installing dependencies)
- **git** (for cloning and for the adeu git dependency)
- **Claude Code** (Anthropic's CLI)

## What It Does

When a counterparty sends back a redlined contract, their tracked changes stay visible. You never "reject" a change in Word -- that makes it vanish with no trace. Instead, the plugin layers your response on top of their markup: deleting their proposed text through your own redline and inserting your alternative, both attributed to you. The counterparty opens Word and sees everything -- their original change, your deletion of it, and your counter-proposal. Full audit trail, full transparency.

When you agree with a counterparty's change, the plugin accepts it -- the markup is removed and the text becomes part of the clean document. That is the only time changes should vanish.

### Features

- **First-pass redlining** of clean contracts with tracked changes and professional comments
- **Multi-round counterparty response** with correctly layered tracked changes preserving the full audit trail
- **Auto-detection** of clean vs redlined documents -- one command handles both workflows
- **Comparison report gate** before applying changes to counterparty redlines -- review before committing
- **Full-autonomy mode** (`/yolo-negotiation`) -- same negotiation logic with all checkpoints removed for when you trust the defaults
- **Word-level surgical diffs** that change only the minimum necessary span of text
- **Professional commenting** -- comments only where they add value, not on every change
- **Configurable persona, authority framework, and playbooks** for different negotiation styles
- **MCP tool annotations** for Claude Desktop directory compliance and security transparency

## Commands

### `/negotiate`

The primary command. Walks you through contract negotiation step by step with checkpoints for review at each stage. Handles both first-pass redlining of clean documents and multi-round counterparty response with layered tracked changes.

### `/yolo-negotiation`

Full-autonomy variant. Same negotiation logic as `/negotiate` but with all checkpoints removed. Use when you trust the defaults and want the finished redlined document in one shot. Amber/red zone authority items are noted in the final report for your review after the fact.

## Architecture Overview

```
Claude-Plugin-MCP/
  .claude-plugin/       Plugin metadata (plugin.json)
  .mcp.json             MCP server configuration
  skills/               Skill definitions for Claude
  commands/             Slash commands (/negotiate, /yolo-negotiation)
  src/                  MCP server source (78 Python files)
    mcp_server/         Tool definitions and server entry point
    ingestion/          Document parsing and validation
    negotiation/        Negotiation logic and evaluation
    pipeline/           Orchestration pipeline
    config/             Three-level config fallback
    models/             Pydantic data models
    validation/         Output validation
  defaults/             Shipped defaults (PERSONA.md, AUTHORITY.md, PLAYBOOK-template.md)
  scripts/              start-mcp.sh launcher
  samples/              Test documents for evaluation
```

**MCP server entry point:** `python -m src.mcp_server`

**Three-level config fallback:** project directory > `~/.config/claude-negotiator/` > shipped defaults in `defaults/`

## Configuration

The plugin works out of the box with sensible defaults. For customisation, place any of the following files in your project directory or `~/.config/claude-negotiator/`:

| File | Purpose |
|------|---------|
| `PERSONA.md` | Define the negotiation persona (tone, formality, jurisdiction conventions) |
| `AUTHORITY.md` | Set authority levels for different clause types (which changes need escalation) |
| `PLAYBOOK-*.md` | Negotiation playbooks for specific deal types (e.g., `PLAYBOOK-SPA.md` for share purchase agreements) |

## Usage Examples

### Example 1: First-Pass Review of a Sales Agreement

**Scenario:** You are a buyer's solicitor reviewing a seller's draft sales agreement for the first time.

```
/negotiate

Review the attached sales agreement from the seller's perspective as buyer's counsel.
Focus on: liability caps (push for mutual caps), indemnification (require
fundamental rep carve-outs), and termination (add termination for convenience
with 30-day notice). Accept standard boilerplate provisions.

[Attach: sales_agreement.docx]
```

**What happens:** Claude ingests the clean document, applies first-pass redlines with tracked changes attributed to you, and adds professional comments where the markup needs explanation. You get back a `.docx` with your proposed changes visible in Word's Track Changes view.

### Example 2: Responding to Counterparty Redlines

**Scenario:** The seller's counsel has returned your redlined agreement with their counter-proposals. You need to respond.

```
/negotiate

Respond to the seller's counter-proposals. They've pushed back on the
liability cap and added a non-compete. Accept their formatting changes
and boilerplate updates. Push back hard on the non-compete (overly broad,
should be limited to 12 months and direct competitors only). Hold firm
on mutual liability caps.

[Attach: sales_agreement_seller_response.docx]
```

**What happens:** Claude detects tracked changes, builds a comparison report showing what the seller accepted, rejected, and added, and presents it for your review. You confirm or adjust before Claude applies your responses as layered tracked changes. The seller will see their original markup alongside your counter-proposals -- full negotiation history preserved.

### Example 3: Multi-Round Negotiation -- Final Positions

**Scenario:** Third round. Most issues are resolved, but the non-compete scope and liability cap amount remain open.

```
/negotiate

Final round. Accept the seller's position on the liability cap at 2x
annual fees -- it's commercially reasonable. Counter-propose on the
non-compete: accept 18-month duration but narrow the geographic scope
to the UK only (not "worldwide"). Add a comment explaining this is our
final position on the non-compete.

[Attach: sales_agreement_round3.docx]
```

**What happens:** Claude layers your final positions on top of the existing multi-round markup. The seller sees the full negotiation history in Word's Review Pane -- every round's changes attributed to the correct party.

### Example 4: Full-Autonomy Negotiation

**Scenario:** You have a straightforward counterparty response and want Claude to handle everything without checkpoints.

```
/yolo-negotiation

Respond to the buyer's redlines on this services agreement. Standard
commercial terms -- accept anything reasonable, push back on uncapped
liability and overly broad IP assignments.

[Attach: services_agreement_buyer_response.docx]
```

**What happens:** Claude ingests the document, shows a brief inline summary of counterparty actions, then immediately evaluates every change and executes the full pipeline -- no comparison report gate, no authority zone pauses, no supervised mode. You get the finished redlined `.docx` in one shot. Any amber/red zone items are noted in the final report for your review after the fact.

### Example 5: Quick Boilerplate Review

**Scenario:** You have received a standard NDA and just want to make sure the basics are covered.

```
/negotiate

Review this NDA as the receiving party. Flag any unusual provisions.
Accept standard mutual confidentiality terms. Push back if the term
exceeds 3 years or if there's a non-solicitation clause buried in it.

[Attach: mutual_nda.docx]
```

**What happens:** Claude redlines the NDA with minimal, targeted changes. Standard provisions pass through unchanged. Only clauses that deviate from market norms get marked up with comments explaining the concern.

## Sample Documents

The `samples/` directory contains generic contracts for testing:

- `clean_sales_agreement.docx` -- a clean sales agreement between fictional parties for testing first-pass redlining
- `redlined_sales_agreement.docx` -- the same agreement with tracked changes (a buyer's first-pass redline) for testing counterparty response

These are fictional documents with no real parties or commercial terms. Use them to evaluate the plugin without needing your own contracts.

## MCP Tools

The plugin exposes 11 MCP tools for contract negotiation:

| Tool | Purpose |
|------|---------|
| `ingest_document` | Read clean and annotated text views from a `.docx` file |
| `get_state_of_play` | Get every tracked change and comment with unique IDs |
| `execute_pipeline` | Run the full negotiation pipeline (counterparty response workflow) |
| `redline_document` | Apply tracked changes to a clean document (first-pass workflow) |
| `accept_changes` | Accept specific tracked changes by ID |
| `counter_propose_changes` | Layer counter-proposals on top of existing tracked changes |
| `add_comments` | Add standalone comments to document text -- supports `ooxml:NNN` anchors |
| `reply_to_comments` | Reply to existing comment threads |
| `resolve_comments` | Mark comment threads as resolved |
| `extract_styler_triplets` | Extract client-authored paragraphs with OOXML context for formatting review |
| `splice_styler_fragments` | Splice corrected OOXML fragments back into the document |

All tools have MCP `ToolAnnotations` declaring `readOnlyHint`, `destructiveHint`, and `openWorldHint` for Claude Desktop compliance.

## `.mcp.json` Setup

The `.mcp.json` file uses `${CLAUDE_PLUGIN_ROOT}` to reference the plugin's `scripts/start-mcp.sh` launcher. Claude Code resolves this variable automatically when you load the plugin with `--plugin-dir`. No manual path editing is needed -- the variable points to wherever you cloned the repository.

## Privacy

Documents are processed entirely on your local machine. The plugin itself makes no network calls -- all OOXML manipulation happens in-process via the Adeu engine.

Claude's conversation (your instructions and the document's text content) goes through Anthropic's API per [Anthropic's privacy policy](https://www.anthropic.com/privacy). The plugin collects no telemetry, no analytics, and makes no external calls beyond what Claude Desktop itself requires.

See [PRIVACY.md](PRIVACY.md) for the full privacy policy.

## Security

See [SECURITY.md](SECURITY.md) for the full security audit, vulnerability reporting process, and responsible disclosure policy.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

This is a proof of concept built using AI-assisted development. It does not provide legal advice and must not be used for live client matters. All output is AI-generated and must be reviewed by a qualified legal professional.

See [DISCLAIMER.md](DISCLAIMER.md) for the full disclaimer.
