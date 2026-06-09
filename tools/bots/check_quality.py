import os
import re
import sys

def check_quality():
    dead_code_pattern = re.compile(r'#\[allow\(dead_code\)\]')
    unused_pattern = re.compile(r'#\[allow\(unused\)\]')
    
    failed = False
    
    for root, _, files in os.walk('.'):
        if '.git' in root or 'target' in root or 'tools' in root:
            continue
            
        for file in files:
            if not file.endswith('.rs'):
                continue
                
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    lines = f.readlines()
                except UnicodeDecodeError:
                    continue
                    
            for i, line in enumerate(lines):
                if dead_code_pattern.search(line) or unused_pattern.search(line):
                    print(f"ERROR: Forbidden #[allow(dead_code)] or #[allow(unused)] found in {path}:{i+1}")
                    print(f"       {line.strip()}")
                    failed = True
                        
    if failed:
        sys.exit(1)
    else:
        print("All source files comply with Code Quality policies.")

if __name__ == '__main__':
    check_quality()
