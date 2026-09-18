#!/usr/bin/env python3
"""Export a native diagram using an installed draw.io Desktop CLI."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def export(source, formats=('svg', 'png'), page=1, out_dir=None, binary=None, timeout=120, overwrite=False):
    source = Path(source).resolve(strict=True)
    if page < 1:
        raise ValueError('page must be 1 or greater')
    binary = binary or os.environ.get('DRAWIO_BIN') or shutil.which('drawio') or shutil.which('draw.io')
    if not binary and Path('/Applications/draw.io.app/Contents/MacOS/draw.io').exists():
        binary = '/Applications/draw.io.app/Contents/MacOS/draw.io'
    if not binary:
        raise RuntimeError('draw.io Desktop not found; set DRAWIO_BIN or pass --binary')
    out_dir = Path(out_dir).resolve() if out_dir else source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem + (f'.page-{page}' if page != 1 else '')
    targets = [out_dir / f'{stem}.{fmt}' for fmt in formats]
    for target in targets:
        if target.exists() and not overwrite:
            raise FileExistsError(f'{target} exists; pass --overwrite to replace')
        if target == source:
            raise ValueError('output must not replace source')
    with tempfile.TemporaryDirectory(prefix='drawio-uml-profile-') as profile, tempfile.TemporaryDirectory(prefix='.drawio-export-', dir=out_dir) as staging:
        for fmt, target in zip(formats, targets):
            output = Path(staging) / target.name
            args = [binary, '--disable-gpu', '--disable-update', '--password-store=basic', '--use-mock-keychain',
                    f'--user-data-dir={profile}', '-x', '-f', fmt, '-e', '-b', '20', '-p', str(page), '-o', str(output), str(source)]
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f'draw.io timed out after {timeout}s for {fmt}; inspect the desktop environment') from exc
            if result.returncode or not output.exists() or output.stat().st_size == 0:
                raise RuntimeError(f'export {fmt} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}')
        # All formats succeeded before any final file is replaced.
        for target in targets:
            os.replace(Path(staging) / target.name, target)
    return targets


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source')
    ap.add_argument('--format', nargs='+', choices=['svg', 'png', 'pdf'], default=['svg', 'png'])
    ap.add_argument('--page', type=int, default=1)
    ap.add_argument('--out-dir')
    ap.add_argument('--binary')
    ap.add_argument('--timeout', type=float, default=120)
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()
    try:
        for target in export(a.source, a.format, a.page, a.out_dir, a.binary, a.timeout, a.overwrite):
            print(target)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Export failed: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
