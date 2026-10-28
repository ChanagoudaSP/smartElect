import os
import shutil
from pathlib import Path

def cleanup_project():
    """Clean up unnecessary files and reduce project size"""
    # Project root
    project_root = Path(__file__).parent
    
    # Files and directories to clean
    cleanup_patterns = [
        # Python cache
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        
        # Logs
        "logs/*.log",
        "logs/*.log.*",
        
        # Cache directories
        "app/data/cache/*",
        ".pytest_cache",
        ".coverage",
        
        # Virtual environment (if not needed)
        # "env",
        # "venv",
        
        # Build and dist directories
        "build",
        "dist",
        "*.egg-info",
        
        # IDE specific
        ".idea",
        ".vscode",
        "*.swp",
        "*.swo",
        
        # Temporary files
        "**/temp",
        "**/tmp",
        "**/.DS_Store"
    ]
    
    total_cleaned = 0
    
    print("Starting cleanup...")
    
    for pattern in cleanup_patterns:
        for path in project_root.glob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                    print(f"Removed file: {path}")
                    total_cleaned += path.stat().st_size
                elif path.is_dir():
                    shutil.rmtree(path)
                    print(f"Removed directory: {path}")
                    total_cleaned += sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
            except Exception as e:
                print(f"Error removing {path}: {e}")
    
    # Convert bytes to MB
    total_cleaned_mb = total_cleaned / (1024 * 1024)
    print(f"\nTotal space cleaned: {total_cleaned_mb:.2f} MB")
    print("Cleanup completed!")

if __name__ == "__main__":
    cleanup_project()
