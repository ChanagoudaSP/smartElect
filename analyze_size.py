import os
from pathlib import Path
import sys
from collections import defaultdict

def get_dir_size(path):
    """Calculate total size of a directory and its subdirectories."""
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def format_size(size):
    """Format size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def analyze_directory(path, min_size_mb=1):
    """Analyze directory sizes recursively."""
    min_size = min_size_mb * 1024 * 1024  # Convert MB to bytes
    sizes = {}
    file_types = defaultdict(int)
    large_files = []

    # Get directory sizes
    for root, dirs, files in os.walk(path):
        # Skip virtual environment directories
        if 'venv' in root.split(os.sep) or 'env' in root.split(os.sep):
            continue
            
        dir_size = 0
        for name in files:
            file_path = os.path.join(root, name)
            try:
                size = os.path.getsize(file_path)
                dir_size += size
                
                # Track file types
                ext = os.path.splitext(name)[1].lower()
                file_types[ext] += size
                
                # Track large files
                if size > min_size:
                    large_files.append((file_path, size))
            except (OSError, FileNotFoundError):
                continue
        
        if dir_size > min_size:
            sizes[root] = dir_size

    # Sort and print results
    print("\nLargest Directories:")
    print("-" * 80)
    for path, size in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"{format_size(size):<15} {path}")

    print("\nLargest File Types:")
    print("-" * 80)
    for ext, size in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"{format_size(size):<15} {ext or '(no extension)'}")

    print("\nLargest Individual Files:")
    print("-" * 80)
    for path, size in sorted(large_files, key=lambda x: x[1], reverse=True)[:20]:
        print(f"{format_size(size):<15} {path}")

if __name__ == '__main__':
    path = "."
    min_size_mb = 1
    if len(sys.argv) > 1:
        min_size_mb = float(sys.argv[1])
    
    print(f"\nAnalyzing directory sizes (showing items larger than {min_size_mb}MB)...")
    analyze_directory(path, min_size_mb)
