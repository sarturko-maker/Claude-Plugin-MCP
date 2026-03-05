---
name: negotiate
description: >
  Negotiate a contract -- provide a Word document and instructions.
  Handles both clean documents (first-pass redlines) and documents with
  existing tracked changes (counterparty response with comparison report).
disable-model-invocation: true
---

# Contract Negotiation

Single entry point for all contract negotiation. The user provides a Word
document and instructions in one prompt. You detect the document type,
route to the correct workflow, and produce a redlined `.docx`.

## Step 1: Gather Context

From the user's message, determine:

- **Document path** -- must be a `.docx` file
- **Instructions** -- what the user wants (brief or detailed)
- **Client author name** -- for Track Changes attribution. Infer from config
  or the user's message. If unclear, ask once.
- **Client role** -- buyer, seller, landlord, etc. Infer from the instructions
  or document context.

Do NOT run a multi-step wizard. Extract what you can from the initial message.
If something critical is missing, ask in one follow-up at most.

## Step 2: Load Configuration

Follow the negotiate-contract skill's Step 1 for configuration loading. The
three-level fallback applies:

1. **Project directory** -- `PERSONA.md`, `AUTHORITY.md`, `PLAYBOOK-*.md`,
   `LOA.md` in the current working directory
2. **Global config** -- `~/.config/claude-negotiator/`
3. **Shipped defaults** -- the plugin's `defaults/` directory

If no custom config exists, the defaults work out of the box. Users can
customise behaviour by placing `PERSONA.md`, `AUTHORITY.md`, or
`PLAYBOOK-*.md` files in their project directory or
`~/.config/claude-negotiator/`.

## Step 3: Ingest and Detect

Call the `ingest_document` MCP tool with the document path. Then determine the
document type by checking the annotated text for CriticMarkup tracked change
markers:

- **No `{++` or `{--` markers** -- this is a **clean document**. A document
  with only comment markers (`{>>`) but no tracked change markers is also
  treated as clean.
- **`{++` or `{--` markers present** -- this document has **existing tracked
  changes**.

## Step 4: Route to Workflow

### Path A -- Clean Document (First-Pass Redlining)

Follow the negotiate-contract skill's First-Pass Redlining Workflow
(Steps A through H). This creates initial tracked changes on the clean
document based on the user's instructions.

### Path B -- Document with Tracked Changes (Counterparty Response)

Follow the negotiate-contract skill's Counterparty Response Workflow
(Steps 3 through 10). This workflow includes a **mandatory comparison report
gate** at Step 3a.

**You MUST:**

1. Build the state of play (Step 3)
2. Present the comparison report to the user (Step 3a)
3. **WAIT for the user to confirm before proceeding**

Do NOT proceed to Step 4 or beyond until the user explicitly confirms. This
gate is non-negotiable -- every counterparty response goes through the
comparison report first. The user may override recommendations, adjust
positions, or give additional instructions before you proceed.

## Quick Reference

### MCP Tools

| Tool | Purpose |
|------|---------|
| `ingest_document` | Read clean and annotated text views |
| `get_state_of_play` | Get every change and comment with IDs |
| `execute_pipeline` | Run the full negotiation pipeline (counterparty response) |
| `redline_document` | Apply tracked changes to a clean document (first-pass) |
| `accept_changes` | Accept specific tracked changes (granular) |
| `counter_propose_changes` | Layer counter-proposals (granular) |
| `add_comments` | Add standalone comments (granular) |
| `reply_to_comments` | Reply to comment threads (granular) |
| `resolve_comments` | Mark comment threads resolved (granular) |

### Key Rule

Never reject a tracked change. Always layer counter-proposals on top of the
counterparty's markup. The counterparty must see their original change
alongside your response -- full audit trail, full transparency.
