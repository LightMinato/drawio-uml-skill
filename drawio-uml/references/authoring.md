# Native Draw.io authoring

Use Python's `xml.etree.ElementTree` (or equivalent XML serialization) to escape labels and keep IDs unique. A file may be a bare `mxGraphModel` or an `mxfile` with named `diagram` pages. Keep source editable; no screenshot-as-diagram substitution.

`scripts/uml_xml.py` offers `Diagram`, `node`, `class_box`, `edge`, `endpoint_label`, and `write`. It serializes explicit positions and waypoints. It deliberately does not infer UML relationships or compute a layout. See `examples/build_examples.py` in the repository for a reproducible class diagram before/after and sequence example.

A minimal builder example (set the actual installed skill path):

```python
import sys
sys.path.insert(0, "/absolute/path/to/drawio-uml/scripts")
from uml_xml import Diagram

d = Diagram("Order model")
d.class_box("order", "Order", ["+ total: Money"], ["+ submit()"], 80, 80)
d.class_box("item", "OrderItem", ["+ quantity: int"], [], 440, 80)
d.edge("contains", "order", "item", kind="composition")
d.endpoint_label("whole", "contains", "1", at="source")
d.endpoint_label("parts", "contains", "1..*", at="target")
d.write("order.drawio")
```

Core native structure:

```xml
<mxfile><diagram id="p1" name="Class diagram"><mxGraphModel grid="1" gridSize="10" page="1" pageWidth="1200" pageHeight="900"><root>
  <mxCell id="0"/>
  <mxCell id="1" parent="0"/>
  <mxCell id="a" value="Customer" vertex="1" parent="1" style="whiteSpace=wrap;html=1;">
    <mxGeometry x="80" y="100" width="220" height="100" as="geometry"/>
  </mxCell>
</root></mxGraphModel></diagram></mxfile>
```

For an edge, use `edge="1"`, source/target IDs, and `<mxGeometry relative="1" as="geometry"/>`. For a connector with deliberately positioned free ends (such as sequence messages), emit `mxPoint as="sourcePoint"` and `mxPoint as="targetPoint"`; keep semantic ownership clear in labels or metadata. Waypoints use `<Array as="points">`. Text at relationship ends is a child vertex of the edge with relative geometry; preserve it during edits.

Relationship styles (source → target):

| Kind | Relevant style | Direction |
| --- | --- | --- |
| Association | `startArrow=none;endArrow=none;` | no implied navigability |
| Directed association | `endArrow=open;endFill=0;` | target is navigable |
| Generalization | `endArrow=block;endFill=0;` | subtype → supertype |
| Realization | `dashed=1;endArrow=block;endFill=0;` | implementing type → interface |
| Dependency | `dashed=1;endArrow=open;endFill=0;` | client → supplier |
| Aggregation | `startArrow=diamond;startFill=0;endArrow=none;` | whole → part |
| Composition | `startArrow=diamond;startFill=1;endArrow=none;` | whole → part |

Each row is an example of native styles, not a reason to overwrite an existing equivalent style. For a new class box, a native rectangle with an HTML table label gives editable text compartments; more elaborate native compartment cells can also be retained. The checker does not verify the semantic correctness of these symbols.

Mermaid conversion is optional if the installed desktop CLI supports the requested notation. Inspect its native result before using it for precise UML. Neither Mermaid nor an automatic layout is required for this skill.

Sources for uncommon shapes and current syntax: [Draw.io XML reference](https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-reference.md), [style reference](https://github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md). These are documentation sources, not runtime dependencies. Use installed CLI help to check version-specific capabilities.
