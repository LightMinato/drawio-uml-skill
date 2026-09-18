# Export

Python 3.10+ runs all bundled scripts using only the standard library. Native `.drawio` creation and editing require no desktop application. Rendering requires draw.io Desktop; no MCP server is required.

```bash
python3 <skill-dir>/scripts/export_diagram.py model.drawio --format svg png
python3 <skill-dir>/scripts/export_diagram.py model.drawio --page 2 --out-dir previews
```

Locate the binary automatically on macOS or PATH, or set `DRAWIO_BIN` / `--binary`. Windows users can pass the executable path. Linux needs a graphical session or an independently configured virtual display. The helper uses a temporary user-data directory, a timeout and captured logs. It does not change HOME or disable Electron's sandbox. An environment restriction should be reported or resolved through the host's normal permission mechanism; do not repeatedly retry identical failures.

Output names are `model.svg` / `model.png` for page 1, and `model.page-2.svg` / `model.page-2.png` for later pages. Existing outputs require `--overwrite`. The native source is never removed. Exports include editable XML. Use the same page number for `verify.py`.

The wrapper verifies that export produced a nonempty file and atomically replaces the target only after success. This does not prove text fits or all content is visible: inspect the image. If rendering is unavailable, deliver native source and state that render/visual verification remains outstanding; do not fabricate a preview or claim visual checks passed.
