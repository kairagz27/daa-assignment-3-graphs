"""Run and retain real local check logs and actual fixture outputs."""
import json
from pathlib import Path
import subprocess
import sys

from oracles import reference

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from public_validate import check


def main():
    evidence = ROOT / 'tests' / 'evidence'
    evidence.mkdir(exist_ok=True)
    commands = [
        ('setup.txt', ['tools/run.py', '--setup']),
        ('public_checks.txt', ['tools/run.py', '--check']),
        ('checker_tools.txt', ['-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py', '-v']),
        ('own_tests.txt', ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']),
        ('actual.jsonl', ['tools/run.py', '--input', 'tests/my_cases.jsonl']),
    ]
    records = []
    for filename, arguments in commands:
        process = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True,
                                 text=True, encoding='utf-8', timeout=120, check=True)
        output = process.stdout if filename == 'actual.jsonl' else process.stdout + process.stderr
        (evidence / filename).write_text(output, encoding='utf-8')
        records.append({'command': 'python ' + ' '.join(arguments), 'exit_code': process.returncode})
        print(f'PASS {records[-1]["command"]}')
    requests = [json.loads(line) for line in (ROOT / 'tests' / 'my_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    answers = [json.loads(line) for line in (evidence / 'actual.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(requests) == len(answers)
    assert all(check(request, answer, reference(request)) for request, answer in zip(requests, answers))
    (evidence / 'commands.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    print(f'PASS all {len(requests)} saved actual outputs satisfy independent expectations.')


if __name__ == '__main__':
    main()
