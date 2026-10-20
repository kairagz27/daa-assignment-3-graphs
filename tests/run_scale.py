"""Run each full-limit case through the real JSON Lines entry point."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src' / 'Python'))
from public_validate import check
from algorithms import reconstruct_route
from generators import scale_cases
from oracles import certify_forest


def main():
    evidence = ROOT / 'tests' / 'evidence'
    evidence.mkdir(exist_ok=True)
    reports = []
    with gzip.open(evidence / 'scale_outputs.jsonl.gz', 'wt', encoding='utf-8') as saved:
        for name, request, expected in scale_cases():
            payload = json.dumps(request, separators=(',', ':')) + '\n'
            started = perf_counter()
            process = subprocess.run([sys.executable, str(ROOT / 'src' / 'Python' / 'main.py')],
                input=payload, capture_output=True, text=True, encoding='utf-8', timeout=20, check=True)
            elapsed = perf_counter() - started
            lines = process.stdout.splitlines()
            assert len(lines) == 1 and not process.stderr
            answer = json.loads(lines[0])
            assert check(request, answer, expected), name
            if request['task'] in ('kruskal', 'prim'):
                certify_forest(request, answer)
            route_length = None
            if request['task'] == 'dag' and expected['acyclic'] and request['edges']:
                route = reconstruct_route(0, request['n'] - 1, request['edges'], answer['parent_edge'])
                assert route == list(range(request['n']))
                route_length = len(route)
            saved.write(json.dumps({'name': name, 'output': answer}, separators=(',', ':')) + '\n')
            report = {'name': name, 'n': request['n'],
                      'm_or_q': len(request.get('edges', request.get('operations', []))),
                      'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
                      'output_sha256': hashlib.sha256(process.stdout.encode()).hexdigest(),
                      'seconds_process_and_json_io': elapsed, 'passed': True,
                      'route_length': route_length}
            reports.append(report)
            print(f"PASS {name}: n={request['n']}, count={report['m_or_q']}, {elapsed:.4f}s", flush=True)
    (evidence / 'scale.json').write_text(json.dumps(reports, indent=2) + '\n', encoding='utf-8')
    print(f'PASS all {len(reports)} full-limit cases (20s limit per process).')


if __name__ == '__main__':
    main()
