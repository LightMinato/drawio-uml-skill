# Layout and connector routing

For a new diagram, lay out the semantic groups before routing. For cleanup, move the fewest elements needed unless a broader redesign was requested.

- Choose a reading direction appropriate to the UML view. Generalization usually reads upward; time in sequence diagrams downward; dependencies can follow layers. One universal vertical flow damages these distinctions.
- Align nodes within groups, reserve whitespace around group boundaries, and use consistent gaps. Begin with roughly 40–80 px between boxes and 16–24 px between nearby parallel routes; adapt to font and density.
- Route class/component relationships orthogonally when it improves tracing. Direct short lines are fine. Keep endpoints on intentional sides; add waypoints only to avoid obstacles or clarify ownership.
- Distribute fan-out ports; do not merge unrelated relationships into one apparent edge. Check the full routes of lines sharing endpoints, not only their attachment region.
- Keep arrowheads, diamonds, role names, guards, and multiplicities clear of corners and other labels. Do not move an endpoint label to the opposite end to make space.
- Prefer reordering related nodes or widening a local gap to adding many bends. If an irreducible crossing remains, place it away from labels and arrowheads and mention it. Crossings alone do not justify changing the model.
- Containers and compartments are intentional nesting. A line through an unrelated class body is a defect; a sequence message crossing a lifeline or an edge entering its target container is not automatically one.

For an existing file, retain custom metadata, pages, layers and native shapes. Do not flatten a class's compartments or sequence frame merely to satisfy a limited geometry parser. Read `verification.md` when a checker cannot measure a shape.
