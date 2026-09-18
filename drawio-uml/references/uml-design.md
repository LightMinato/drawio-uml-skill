# UML design decisions

Read only the section for the requested view. This is a practical notation guide, not a complete UML specification.

| View | Organize around | Preserve when tidying |
| --- | --- | --- |
| Class | responsibility clusters; superclass above subclasses | attributes, operations, visibility, types, stereotypes, multiplicity, relation kinds |
| Sequence | participants left to right; time downward | message order, synchronous/asynchronous/reply arrows, activations, alt/opt/loop guards |
| Activity | dominant flow; responsibility lanes if useful | guards, decisions versus merges, fork/join bars, initial and final nodes |
| State | lifecycle stages; transitions near related states | initial/final pseudostates, composite states, event [guard] / effect labels |
| Use case | actors outside a named system boundary | actor associations, generalization, include/extend direction and labels |
| Component | responsibility or dependency layers | interfaces, ports, required/provided interfaces, dependency direction |
| Deployment | nested runtime nodes and artifacts | deployment containment, communication paths, runtime versus logical elements |

## Class

Use separate name, attributes, and operations compartments when those details are requested. Keep class names centered and members left aligned. Size by the longest meaningful line, then equalize within a row; avoid huge empty boxes merely to force global uniformity.

A generalization's hollow triangle points to the superclass. Realization uses a dashed line and hollow triangle toward the interface. A composition's filled diamond is at the **whole**, aggregation's hollow diamond also at the whole. Association is a solid line; navigability arrows only when specified. Dependency is dashed with an open arrow toward the supplier. Do not infer composition solely from a field reference.

Place multiplicities at relationship ends, not in a shared central label. Preserve role names and navigability. Avoid sharing a trunk between independent associations when it makes multiplicities ambiguous.

## Sequence

Keep lifeline headers aligned; put messages on distinct time rows. A synchronous call normally has a filled triangular arrow, an asynchronous message an open arrow, a reply a dashed open arrow. Do not turn messages into arbitrary orthogonal detours: their vertical position carries meaning. Use a rectangular return for self-messages and respect activation nesting. Group fragments with a frame and guards; crossings of messages and intermediate lifelines are expected, not generic layout defects.

## Activity and state

Activity decisions may have two or more guarded outgoing flows; merges can have several incoming flows and one outgoing flow. No requirement for literal yes/no labels. Fork/join bars express concurrency; a decision diamond does not. For state transitions, keep labels close to their route and preserve self-loops and composite state boundaries.

## Use case, component, deployment

Use case ellipses belong inside the system boundary; actors usually outside. `«include»` points from including to included use case; `«extend»` points from extension to the base. For components and deployment use explicit stereotypes or native UML shapes rather than decorative cloud icons with uncertain meaning. A minimal rectangle with an explicit stereotype is preferable to a guessed symbol.

## Visual defaults

White background; dark slate text; subdued borders; one muted blue accent for interfaces or a relevant category. Start near 14–16 px body text and 18 px names, adapting to final viewing size. Use the user's language and a font available to the renderer. Give labels padding and place relationship labels on open segments. Color supplements notation; it never replaces arrow types, guards, or stereotypes.
