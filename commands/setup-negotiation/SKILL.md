---
name: setup-negotiation
description: >
  Set up your negotiation profile — persona, authority framework, and
  optional playbook. Run this once to personalise how the negotiation
  assistant works. Saves config to ~/.config/claude-negotiator/.
disable-model-invocation: true
---

# Negotiation Profile Setup

Guide the user through a brief conversational intake to build their negotiation
profile. This is a one-time setup, not a blocking requirement — the plugin
works out of the box with sensible defaults.

## The Conversation

Keep it brief and natural — like a short intake meeting, not an interrogation.
Four questions, clear options, done in under a minute.

### 1. Practice Type

Are you in-house counsel (fixed client, your organisation) or in private
practice (different clients per engagement)?

This affects how you frame "your client" in the persona.

### 2. Practice Area

What type of contracts do you typically negotiate? Commercial, corporate,
IP/technology, employment, real estate, etc.

This adjusts the persona's domain focus and judgment baseline.

### 3. Negotiation Style

Do you prefer:
- **Conservative** — flag everything, minimal autonomous action
- **Moderate** (default) — balanced green/amber/red zones
- **Aggressive** — push back harder, wider green zone

This calibrates the authority framework boundaries.

### 4. Risk Tolerance

One or two questions about comfort with autonomous action. For example:
- "Are you comfortable with me accepting changes to standard boilerplate
  without flagging them?"
- "Should I flag all changes to financial thresholds, even small ones?"

Use answers to adjust the boundary between green and amber zones.

## After the Conversation

Based on the answers, generate tailored `PERSONA.md` and `AUTHORITY.md`
content. Then save using the `write_global_config` function (via the MCP
tools or directly) to `~/.config/claude-negotiator/`.

Confirm to the user that the profile has been saved and will be used for
all future negotiations. Mention they can also create project-level
overrides by placing `PERSONA.md`, `AUTHORITY.md`, or `PLAYBOOK-*.md`
files in their project directory.

## Defaults Reference

If the user declines setup, the shipped defaults are:
- **Persona:** Conservative commercial solicitor, collaborative but firm
- **Authority:** Wide amber zone — flags payment terms, liability caps,
  indemnities, warranties, termination, IP, confidentiality, force majeure,
  assignment, and any change that shifts commercial risk
- **Green zone:** Typos, formatting, standard boilerplate, defined term
  consistency, cross-references
- **Red zone:** Governing law, jurisdiction, regulatory compliance, sanctions,
  data protection, unlimited liability exposure, anything unclear
