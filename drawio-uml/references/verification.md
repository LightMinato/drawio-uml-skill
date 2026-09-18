# What the checker can establish

`verify.py source.drawio render.svg --page 1 --json` compares source cell IDs with SVG geometry. It reports structural errors, missing or unsupported geometry, proper connector crossings, connector/body intersections, node overlaps, and proximity warnings. Label collisions and text clipping are not automatically checked in this version; inspect them visually.

Exit codes: **0** = supported checks completed without hard findings; **1** = hard layout findings; **2** = malformed input or incomplete/unsupported measurement. Warnings do not automatically fail. `--strict` promotes geometry warnings such as crossings and proximity to failures; it still cannot establish UML correctness.

A missing SVG cell must not silently count as clean. Curves are sampled for geometry and reported as approximate. Unsupported transforms, shapes, or label structures are disclosed. The checker primarily targets ordinary box/ellipse/polygon UML views with line connectors. Complex native UML symbols and sequence lifelines may require manual review; preserve them rather than rewriting notation to satisfy the checker. No browser text-layout measurements are performed.

Crossings are warnings by default because some graphs cannot be drawn without them. Shared source/target does not exempt a pair's entire route. Exact shared endpoints are excluded from proper-crossing checks; overlapping routes are separately reported. Parent/child containment is excluded from node overlap checks. Edges may enter their own source/target ancestors. The checker does not enforce yes/no decision branches.

Use `compare_semantics.py before.drawio after.drawio` during cleanup: it compares all pages' IDs, labels, non-geometric styles, ownership and relationship endpoints while allowing geometry and selected cosmetic styles to change. It is conservative: review differences for intentional changes. It does not prove full UML conformance. Preserve page IDs and model details when editing.

Review whole-page reading order, compartment separators, association ends, multiplicities, guards, stereotype text, and sequence order independently. A report and a preview complement each other.
