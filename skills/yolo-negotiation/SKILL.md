---
name: yolo-negotiation
description: >
  Negotiate a contract with full autonomy -- no checkpoints, no gates.
  Provide a Word document and instructions. Claude reads, decides, and
  executes the full pipeline without stopping. Configuration files still
  inform judgment but never pause execution.
disable-model-invocation: true
---

# Autonomous Contract Negotiation

Full-autonomy negotiation command. Same negotiation logic as `/negotiate` but
with all checkpoints removed. Claude reads the document, makes every decision
autonomously, and executes the full pipeline without stopping.

Configuration files (persona, authority, playbook) are still loaded and used to
**inform** Claude's judgment -- they shape decision quality but never gate
execution.

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
(Steps A through H) with these modifications:

- **Step C (Authority Check):** Classify changes against the authority
  framework for decision quality, but do NOT pause for amber or red zone
  items. Note them in the final report instead. Proceed immediately.
- **Step E (Commenting Rules):** Same rules apply unchanged.

### Path B -- Document with Tracked Changes (Counterparty Response)

Follow the negotiate-contract skill's Counterparty Response Workflow
(Steps 3 through 10) with these modifications:

- **Step 3a (Comparison Report):** Show a brief inline summary of what the
  counterparty did (accepted, pushed back, added new) but do NOT wait for
  user confirmation. Display it and immediately proceed to evaluation.
- **Step 5a (Authority Check):** Classify decisions against the authority
  framework for decision quality, but do NOT pause for amber or red zone
  items. Note them in the final report instead. Proceed immediately.
- **Step 7 (Autonomy Mode):** Always fully autonomous. Do not offer supervised
  mode. Build the full decision list and execute the pipeline in one go.

## Differences from `/negotiate`

| Gate | `/negotiate` | `/yolo-negotiation` |
|------|-------------|---------------------|
| Comparison report | Mandatory wait for confirmation | Shown inline, no wait |
| Authority zones (amber) | Pause and ask for guidance | Note in report, proceed |
| Authority zones (red) | Escalate immediately, do not act | Note in report, proceed |
| Supervised mode | Available for complex negotiations | Never offered |

All other negotiation logic is identical: materiality test, commenting rules,
layering behaviour, edit precision, styler pass, and MCP tool usage.

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
| `add_comments` | Add standalone comments (granular) -- use `ooxml:NNN` anchors after mutations |
| `reply_to_comments` | Reply to comment threads (granular) |
| `resolve_comments` | Mark comment threads resolved (granular) |

### Key Rule

Never reject a tracked change. Always layer counter-proposals on top of the
counterparty's markup. The counterparty must see their original change
alongside your response -- full audit trail, full transparency.
