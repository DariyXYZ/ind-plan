"""Rebuild all derived library artifacts from the configured sheet extracts."""
import json
import os
import subprocess
import sys
from pathlib import Path

from build_db import build
from coverage import main as coverage

ROOT = Path(__file__).resolve().parent


if __name__ == '__main__':
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    output = ROOT / 'out_rebuilt'
    output.mkdir(exist_ok=True)
    arguments = [f"{ROOT / s['directory']}|{s['prefix']}|{s['project']}" for s in sources]
    result = subprocess.run([sys.executable, str(ROOT / 'analyze.py'), str(output), *arguments],
                            capture_output=True, text=True, encoding='utf-8', check=True,
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    print(result.stdout.splitlines()[-1])
    plans = build(output / '_library.json')
    coverage()
    import to_contour_graph
    sys.argv = [sys.argv[0], str(ROOT / 'db' / 'library.json')]
    to_contour_graph.main()
    print(f'Rebuilt {len(plans)} plans and coverage.md')
