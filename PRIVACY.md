# Privacy Policy -- Contract Negotiator Plugin

## Overview

This plugin processes legal documents locally on your machine. No data is collected, stored, or transmitted by the plugin itself.

## How It Works

The plugin runs as a local MCP server. Document parsing, XML manipulation, and tracked change operations happen entirely on your machine using the [Adeu](https://github.com/dealfluence/adeu) library -- an open-source Python package that performs all document processing locally.

## Claude API Interaction

When you use this plugin through Claude Desktop, your conversation -- including document text you share with Claude -- is processed through Anthropic's API. This is standard Claude behavior, not specific to this plugin. The plugin itself makes no API calls; it is Claude that sends and receives data through Anthropic's infrastructure.

Refer to [Anthropic's Privacy Policy](https://www.anthropic.com/privacy) for details on how Anthropic handles conversation data.

## No Telemetry

This plugin does not collect analytics, usage metrics, crash reports, or any form of telemetry. There are no external API calls from the plugin itself.

## No Data Storage

The plugin is stateless. It does not maintain any persistent storage, databases, or caches between sessions. Documents are processed in memory and results are written to the output path you specify.

## Contact

For privacy questions, open a GitHub issue at [https://github.com/sarturko-maker/Claude-Plugin-MCP/issues](https://github.com/sarturko-maker/Claude-Plugin-MCP/issues) or email the maintainer.

---

*Last updated: 2026-03-05*
