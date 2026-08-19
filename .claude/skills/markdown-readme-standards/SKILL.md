---
name: markdown-readme-standards
description: Core guidelines and formatting rules for writing professional README files and Markdown documents in this repo, prioritizing tables, bullet points, and simple English. Use when creating or updating markdown documentation.
---

# README & Markdown Standards

## 1. Core Principles
* **Keep it Simple:** Use plain, clear, and easy-to-understand English. Avoid complex jargon.
* **Scan & Read:** Prioritize bullet points and tables for quick information scanning. Avoid dense blocks of text.
* **Structure First:** Every document must follow a logical hierarchy using standard Markdown headings.

## 2. Standard README Structure (Template)

| Section | Purpose & Content |
| :--- | :--- |
| **Title & Badge** | Clear project name, version, and status badges. |
| **Overview** | A 2-3 sentence summary of what the project does and why it exists. |
| **Architecture** | Brief description or text-based layout of components. |
| **Getting Started** | Prerequisites and quick setup steps. |
| **Usage** | Practical examples or CLI commands. |
| **Roadmap** | Planned features or upcoming development phases. |

## 3. Formatting Rules
* **Tables:** Use markdown tables for comparing options, listing configurations, or mapping directories.
* **Lists:** Use unordered bullet points (`*` or `-`) for features, requirements, and steps. Use numbered lists (`1.`, `2.`) only for strict sequential workflows.
* **Code Blocks:** Always specify the language identifier for code snippets (e.g., ```bash, ```python, ```yaml).
* **Links:** Use relative links for internal documentation paths (e.g., `[Architecture Docs](./docs/architecture.md)`).

## 4. Markdown Anti-Patterns
* **No Wall of Text:** Break paragraphs longer than 3 sentences into bullet points.
* **No Broken Links:** Ensure all local file links and anchor tags point to existing destinations.
* **No Missing Setup Steps:** Never assume dependencies (like Node, Python, or Docker) are globally known; always list prerequisites.