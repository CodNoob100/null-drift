import os
import re
import sys
import subprocess
from datetime import datetime, timedelta, timezone

def check_todos():
    todo_pattern = re.compile(r'(?i)TODO')
    issue_pattern = re.compile(r'(?i)TODO\s*\(\s*(issue|#|https://github\.com/)[^)]+\)')
    
    failed = False
    now = datetime.now(timezone.utc)
    
    for root, _, files in os.walk('.'):
        if 'tools/bots' in root or 'tools\\bots' in root or '.git' in root or 'target' in root:
            continue
            
        for file in files:
            if not (file.endswith('.rs') or file.endswith('.py')):
                continue
                
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    lines = f.readlines()
                except UnicodeDecodeError:
                    continue
                    
            for i, line in enumerate(lines):
                if todo_pattern.search(line):
                    line_num = i + 1
                    if not issue_pattern.search(line):
                        print(f"ERROR: TODO without issue link found in {path}:{line_num}")
                        print(f"       {line.strip()}")
                        failed = True
                    
                    # Enforce 30-day rule using git blame
                    try:
                        result = subprocess.run(
                            ['git', 'blame', '-L', f'{line_num},{line_num}', '--line-porcelain', path],
                            capture_output=True, text=True, check=True
                        )
                        for out_line in result.stdout.splitlines():
                            if out_line.startswith('committer-time '):
                                timestamp = int(out_line.split(' ')[1])
                                commit_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                                age = now - commit_date
                                if age.days > 30:
                                    print(f"ERROR: TODO is older than 30 days ({age.days} days) in {path}:{line_num}")
                                    print(f"       {line.strip()}")
                                    failed = True
                                break
                    except Exception:
                        pass
                        
    if failed:
        sys.exit(1)
    else:
        print("All TODOs comply with CONTRIBUTING.md rules.")

if __name__ == '__main__':
    check_todos()
