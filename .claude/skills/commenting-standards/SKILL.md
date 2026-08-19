---
name: commenting-standards
description: Core guidelines for writing clean code comments, Google-style docstrings, AI-driven tags, and concise explanations to optimize code readability and Claude Code comprehension.
---

# Code Commenting & Documentation Standards

## 1. Core Principles
* **Why over What:** Explain business context, architectural decisions, or bug fixes, not code mechanics.
* **Concise Explanations:** Keep inline comments and explanatory notes extremely brief (maximum 1 sentence / under 10-12 words) to prevent clutter.
* **AI & Human Friendly:** Clear comments prevent AI guesswork and improve code generation accuracy.
* **Self-Documenting:** Use clear naming for variables, functions, and classes before writing comments.
* **Keep Updated:** Outdated comments are strictly prohibited; update them alongside code changes.

## 2. Language-Specific Guidelines
* **YAML:** Explain configuration parameters or environment context *above* the key. Do not repeat the key name.
* **Python:** 
  * Mandatory Google-style Docstrings (PEP 257) for all Modules, Classes, and Public Functions/Methods.
  * Use type hints instead of describing types in comments.
  * Inline comments require `#` and must be separated by at least 2 spaces (keep explanations short).
* **TypeScript:** 
  * Use TSDoc/JSDoc (`/** ... */`) for exports, components, interfaces, and types.
  * Do not duplicate TypeScript types within documentation.

## 3. AI-Driven Tags (Claude Code Optimization)
* `// TODO:` / `# TODO:`: Unfinished features or improvements for AI code generation.
* `// FIXME:` / `# FIXME:`: Known bugs or urgent code needing refactoring.
* `// NOTE:` / `# NOTE:`: Workarounds or counterintuitive edge cases required to prevent system failures.

## 4. Anti-Patterns to Avoid
* **Obvious Comments:** Do not explain self-explanatory code (e.g., `i++ // Increment i`).
* **Verbose Explanations:** Avoid multi-sentence paragraphs inside inline comments; keep them punchy.
* **Commented-out Code:** Delete dead code; rely on Git history instead. Confuses AI parsers.
* **Stale Comments:** Delete or update comments that no longer match the active code logic.