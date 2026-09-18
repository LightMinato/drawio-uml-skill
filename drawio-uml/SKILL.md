---
name: drawio-uml
description: "Create and tidy editable UML diagrams in Draw.io, with clear hierarchy, readable labels, and deliberate connector routing. Use for UML drawing or layout cleanup."
---

# Draw.io UML

Create UML diagrams from requirements, or improve an existing `.drawio` without changing its meaning. Deliver editable source and a readable preview when a renderer is available. This skill is self-contained: no other skill or MCP server is required.

## Choose the work

- **Create:** choose the UML view that answers the user's question. Read [UML design](references/uml-design.md) for the relevant diagram type, then [authoring](references/authoring.md) for XML and relationship styles. Start with the essential model; add detail only if it serves the requested view.
- **Tidy:** preserve IDs, labels, members, stereotypes, relationship types, direction, multiplicities, guards, message order, and unrelated pages. Read [layout and routing](references/layout-routing.md). Save a new file unless the user requests an in-place update. Use `scripts/compare_semantics.py` to identify structural differences; explain intentional changes.
- **Audit:** inspect the source and, when available, a fresh SVG. Read [verification](references/verification.md) to distinguish supported geometry checks from visual and semantic review.

Primary scope: class, sequence, activity, state, use-case, component, and deployment diagrams. Do not apply activity-flow rules to other UML views. For ambiguous requests choose the simplest relevant view and state the assumption; ask only when the missing relationship meaning would change the model.

## Design standard

Correct UML semantics come before aesthetics. Use aligned groups, generous whitespace, consistent type and node sizing, neutral surfaces, and at most a few meaningful accent colors. Preserve a supplied visual style unless asked to redesign it. Reduce bends, crossings, overlaps, and long detours together; zero crossings is not a universal requirement.

Use native XML for precise UML notation and editable elements. Small edits can be made directly; a generator is useful for repetitive or frequently regenerated diagrams, not mandatory. `scripts/uml_xml.py` supplies a small optional XML builder and relationship styles; it is not an automatic layout engine. See [authoring](references/authoring.md).

## Render and finish

Resolve script paths relative to this skill directory; do not assume it is the working directory.

```bash
python3 <skill-dir>/scripts/export_diagram.py diagram.drawio --format svg png
python3 <skill-dir>/scripts/verify.py diagram.drawio diagram.svg --json
# When tidying an existing file:
python3 <skill-dir>/scripts/compare_semantics.py original.drawio diagram.drawio
```

Export and audit use **1-based page numbers** (`--page 1`). For multiple pages, export and review each changed page. Read [export](references/export.md) only for rendering or environment problems.

Inspect the complete rendered diagram at reading size and zoom into dense areas. Fix accidental node overlap, clipped text, misleading arrowheads, unreadable labels, and connectors passing through unrelated nodes. Review checker warnings against UML semantics: sequence messages intentionally cross lifelines, containment can be intentional, and nonplanar graphs may retain crossings. Do not change relationship meaning to silence a check.

A result is complete when the requested content and UML notation are preserved, the available checks have been reviewed, and the editable `.drawio` plus requested previews are delivered. State any unresolved layout issue or unavailable render check. A checker result is not a certificate of visual quality or UML conformance. Do not delete source files after exporting.
