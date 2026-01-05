"""
This script gathers content from all configuration files in blastFoam tutorial cases
and consolidates them into multiple text files, one for each case. This output is
designed to be used as input for a Large Language Model (LLM).
"""

import os
from tqdm import tqdm

# --- Configuration ---
TUTORIALS_ROOT_DIR = '/home/oseasy/lsh_cases/blastFoam-cases-dataset/blastFoam_tutorials'
OUTPUT_DIR = '/home/oseasy/lsh_cases/blastFoam-cases-dataset/case_content_bundles'
# Optional: Specify cases to process. If empty, all found cases will be processed.
CASES_TO_PROCESS = []

# --- Helper Functions ---

def is_case_directory(dir_path):
    """Check if a directory is a valid OpenFOAM case directory."""
    return os.path.isdir(os.path.join(dir_path, 'system')) and \
           os.path.isdir(os.path.join(dir_path, 'constant'))

def find_case_directories(root_dir):
    """Find all case directories recursively."""
    case_dirs = []
    if CASES_TO_PROCESS:
        for case_path in CASES_TO_PROCESS:
            full_path = os.path.join(root_dir, case_path)
            if is_case_directory(full_path):
                case_dirs.append(full_path)
            else:
                print(f"Warning: Specified case '{full_path}' is not a valid case directory.")
    else:
        for dirpath, _, _ in os.walk(root_dir):
            if is_case_directory(dirpath):
                # Avoid adding sub-cases if a parent case is already found
                is_sub_case = any(dirpath.startswith(d) and dirpath != d for d in case_dirs)
                if not is_sub_case:
                    case_dirs.append(dirpath)
    return case_dirs

def find_config_files(case_dir):
    """Find all configuration files in a case directory's 'system', 'constant', and '0' dirs."""
    config_files = []
    # Process '0' directory first if it exists, then 'constant', then 'system'
    for subdir in ['0', 'constant', 'system']:
        sub_path = os.path.join(case_dir, subdir)
        if os.path.isdir(sub_path):
            for root, _, files in os.walk(sub_path):
                for file in sorted(files): # Sort files for consistent ordering
                    # Simple heuristic: ignore hidden files, backups, and compiled files
                    if not file.startswith('.') and not file.endswith('~') and not '.so' in file and not file.lower().endswith('.stl'):
                        config_files.append(os.path.join(root, file))
    return config_files

# --- Main Logic ---

def main():
    """Main function to generate the consolidated text files for each case."""
    print("Starting to gather file contents into separate files per case...")

    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory set to: {OUTPUT_DIR}")

    print("Scanning for case directories...")
    case_dirs = find_case_directories(TUTORIALS_ROOT_DIR)
    print(f"Found {len(case_dirs)} case directories to process.")

    for case_dir in tqdm(case_dirs, desc="Processing cases"):
        case_rel_path = os.path.relpath(case_dir, TUTORIALS_ROOT_DIR)
        # Create a safe filename from the relative path
        output_filename = case_rel_path.replace('/', '_') + '.txt'
        output_filepath = os.path.join(OUTPUT_DIR, output_filename)

        config_files = find_config_files(case_dir)

        if not config_files:
            continue

        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            for file_path in config_files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                        relative_path = os.path.relpath(file_path, TUTORIALS_ROOT_DIR)

                        outfile.write(f"--- FILE: {relative_path} ---\n")
                        outfile.write(content)
                        # Ensure the file content ends with a newline before the footer
                        if not content.endswith('\n'):
                            outfile.write('\n')
                        outfile.write("--- END OF FILE ---\n\n")
                except Exception as e:
                    print(f"Could not read or write file {file_path}: {e}")

    print(f"\nProcessing complete.")
    print(f"All case contents have been written to individual files in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
