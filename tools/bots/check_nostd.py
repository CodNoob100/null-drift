import os
import re
import sys

def check_nostd():
    alloc_pattern = re.compile(r'extern\s+crate\s+alloc')
    std_pattern = re.compile(r'use\s+std::')
    
    failed = False
    
    for root, _, files in os.walk('.'):
        if '.git' in root or 'target' in root or 'tools' in root:
            continue
            
        for file in files:
            if not file.endswith('.rs') or 'build.rs' in file:
                continue
                
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    lines = f.readlines()
                except UnicodeDecodeError:
                    continue
                    
            for i, line in enumerate(lines):
                if alloc_pattern.search(line) or std_pattern.search(line):
                    print(f"ERROR: std or alloc usage found in {path}:{i+1} (Violates Zero-Heap / no_std policy)")
                    print(f"       {line.strip()}")
                    failed = True
                        
    if failed:
        sys.exit(1)
    else:
        print("All source files comply with no_std / zero-heap policy.")

if __name__ == '__main__':
    check_nostd()
