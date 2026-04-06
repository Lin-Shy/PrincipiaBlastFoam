import os
import shutil
import argparse
import re
from pathlib import Path

def is_time_directory(name):
    """
    Check if a directory name represents a time step (number).
    OpenFOAM time directories are usually numbers (int or float).
    '0' is considered an initial directory and should be kept.
    """
    if name == '0' or name == '0.orig':
        return False
    
    # Check if it looks like a number
    try:
        float(name)
        return True
    except ValueError:
        return False

def ignore_patterns(path, names):
    """
    Callback for shutil.copytree to determine which files/folders to ignore.
    """
    ignored = set()
    for name in names:
        full_path = os.path.join(path, name)
        
        # Always ignore processor directories (parallel run results), matching processor*
        if name.startswith('processor') and os.path.isdir(full_path):
            ignored.add(name)
            continue
            
        # Ignore postProcessing folder
        if name == 'postProcessing':
            ignored.add(name)
            continue
            
        # Ignore time directories (results), but keep '0'
        if os.path.isdir(full_path) and is_time_directory(name):
            ignored.add(name)
            continue
            
        # Ignore log files
        if name.startswith('log.') or name.endswith('.log'):
            ignored.add(name)
            continue
            
        # Ignore dynamicCode
        if name == 'dynamicCode':
            ignored.add(name)
            continue

        # Ignore other common generated folders in OpenFOAM
        if name in ['VTK', 'probe', 'forces']:
             if os.path.isdir(full_path):
                ignored.add(name)
    
    return ignored

def copy_openfoam_case(src, dst):
    """
    Copies an OpenFOAM case from src to dst, ignoring result files.
    """
    src_path = Path(src).resolve()
    dst_path = Path(dst).resolve()

    if not src_path.exists():
        print(f"Error: Source path '{src}' does not exist.")
        return

    if dst_path.exists():
        print(f"Error: Destination path '{dst}' already exists. Please provide a new path.")
        return

    print(f"Copying OpenFOAM case from '{src}' to '{dst}'...")
    print("Ignoring result directories (time steps > 0, postProcessing, processor*, etc.)")

    try:
        shutil.copytree(src_path, dst_path, ignore=ignore_patterns)
        print("Copy completed successfully.")
    except Exception as e:
        print(f"An error occurred during copy: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy an OpenFOAM case ignoring result files.")
    parser.add_argument("source", help="Path to the source OpenFOAM case")
    parser.add_argument("destination", help="Path for the new copy")

    args = parser.parse_args()

    copy_openfoam_case(args.source, args.destination)
