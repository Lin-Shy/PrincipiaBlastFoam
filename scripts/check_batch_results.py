import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL")

# Configuration
MODIFICATIONS_FILE = "/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/data/blastfoam_modifications.json"
OUTPUT_BASE_DIR = "/media/dev/vdb1/linshihao/LLM/LLM-output-cases/batch_runs"
BATCH_RESULTS_FILE = os.path.join(OUTPUT_BASE_DIR, "batch_execution_results.json")
VERIFICATION_RESULTS_FILE = os.path.join(OUTPUT_BASE_DIR, "verification_results.json")


def llm():
    """Provides a ChatOpenAI instance."""
    return ChatOpenAI(
        base_url=LLM_API_BASE_URL,
        model=LLM_MODEL_NAME,
        api_key=LLM_API_KEY,
        temperature=0.1,
    )


def load_modifications():
    """Load modifications from JSON file."""
    with open(MODIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_batch_results():
    """Load batch execution results."""
    if not os.path.exists(BATCH_RESULTS_FILE):
        print(f"❌ Batch results file not found: {BATCH_RESULTS_FILE}")
        return None
    
    with open(BATCH_RESULTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_modified_files(case_path, modified_files):
    """
    Read the content of modified files from the generated case.
    
    Args:
        case_path: Path to the generated case
        modified_files: List of relative paths to modified files
        
    Returns:
        Dictionary mapping file paths to their content
    """
    files_content = {}
    
    for file_path in modified_files:
        full_path = os.path.join(case_path, file_path)
        
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files_content[file_path] = content
            except Exception as e:
                files_content[file_path] = f"Error reading file: {str(e)}"
        else:
            files_content[file_path] = "File not found"
    
    return files_content


def verify_case_with_llm(llm_instance, case_info, files_content):
    """
    Use LLM to verify if the modified files match the requirements.
    
    Args:
        llm_instance: ChatOpenAI instance
        case_info: Dictionary containing case information
        files_content: Dictionary of file contents
        
    Returns:
        Dictionary containing verification results
    """
    # Prepare the prompt
    system_prompt = """You are an expert at verifying OpenFOAM case configurations.
Your task is to check if the modified files correctly implement the requested changes.

Analyze the file contents and determine:
1. Whether the modification was correctly applied
2. Whether the values/settings match the requirements
3. Any issues or discrepancies found

Respond in JSON format with the following structure:
{
    "verification_passed": true/false,
    "confidence": "high/medium/low",
    "findings": "Detailed explanation of what was checked and found",
    "issues": ["List of any issues found"],
    "correct_modifications": ["List of correctly applied modifications"]
}"""

    # Build the user message with case details
    user_message = f"""Please verify the following OpenFOAM case modification:

**Case Name:** {case_info['case_name']}

**Requirement Description:** {case_info['description']}

**Specific Modification Required:** {case_info['modification']}

**Modified Files:** {', '.join(case_info['modified_files'])}

**File Contents:**
"""
    
    for file_path, content in files_content.items():
        user_message += f"\n\n--- File: {file_path} ---\n"
        if content == "File not found":
            user_message += "❌ File not found in the generated case.\n"
        elif content.startswith("Error reading file:"):
            user_message += f"❌ {content}\n"
        else:
            # Limit content length to avoid token limits
            if len(content) > 5000:
                user_message += content[:5000] + "\n... (content truncated)"
            else:
                user_message += content
    
    user_message += "\n\nPlease verify if the modifications match the requirements."
    
    try:
        # Call LLM
        response = llm_instance.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        # Parse response
        response_text = response.content.strip()
        
        # Try to extract JSON from the response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        try:
            verification_result = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a structured result from text
            verification_result = {
                "verification_passed": "successfully" in response_text.lower() or "correct" in response_text.lower(),
                "confidence": "low",
                "findings": response_text,
                "issues": [],
                "correct_modifications": []
            }
        
        return verification_result
        
    except Exception as e:
        return {
            "verification_passed": False,
            "confidence": "low",
            "findings": f"Error during verification: {str(e)}",
            "issues": [str(e)],
            "correct_modifications": []
        }


def verify_single_case(llm_instance, modification, index, total):
    """
    Verify a single case result.
    
    Args:
        llm_instance: ChatOpenAI instance
        modification: Dictionary containing case modification details
        index: Current case index
        total: Total number of cases
        
    Returns:
        Dictionary containing verification results
    """
    case_name = modification['case_name']
    case_path = os.path.join(OUTPUT_BASE_DIR, case_name)
    
    print(f"\n{'='*80}")
    print(f"🔍 Verifying Case [{index}/{total}]: {case_name}")
    print(f"{'='*80}")
    print(f"📝 Requirement: {modification['description']}")
    print(f"🔧 Modification: {modification['modification']}")
    
    verification_result = {
        "case_name": case_name,
        "case_path": case_path,
        "requirement": modification['description'],
        "modification": modification['modification'],
        "modified_files": modification['modified_files'],
        "verification_time": datetime.now().isoformat(),
        "status": "pending"
    }
    
    # Check if case directory exists
    if not os.path.exists(case_path):
        print(f"❌ Case directory not found: {case_path}")
        verification_result['status'] = 'failed'
        verification_result['reason'] = 'Case directory not found'
        verification_result['llm_verification'] = None
        return verification_result
    
    # Read modified files
    print(f"📂 Reading modified files...")
    files_content = read_modified_files(case_path, modification['modified_files'])
    
    # Check if files exist
    missing_files = [f for f, c in files_content.items() if c == "File not found"]
    if missing_files:
        print(f"⚠️  Missing files: {', '.join(missing_files)}")
        verification_result['status'] = 'partial'
        verification_result['missing_files'] = missing_files
    
    # Verify with LLM
    print(f"🤖 Verifying with LLM...")
    llm_verification = verify_case_with_llm(llm_instance, modification, files_content)
    verification_result['llm_verification'] = llm_verification
    
    # Determine overall status
    if missing_files:
        verification_result['status'] = 'failed'
        verification_result['reason'] = f"Missing files: {', '.join(missing_files)}"
    elif llm_verification.get('verification_passed', False):
        verification_result['status'] = 'passed'
        verification_result['reason'] = 'Modifications correctly applied'
        print(f"✅ Verification PASSED")
    else:
        verification_result['status'] = 'failed'
        verification_result['reason'] = 'Modifications do not match requirements'
        print(f"❌ Verification FAILED")
    
    # Show findings
    if llm_verification.get('findings'):
        print(f"📋 Findings: {llm_verification['findings'][:200]}...")
    
    if llm_verification.get('issues'):
        print(f"⚠️  Issues found: {', '.join(llm_verification['issues'])}")
    
    return verification_result


def save_verification_results(results):
    """Save verification results to JSON file."""
    with open(VERIFICATION_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Verification results saved to: {VERIFICATION_RESULTS_FILE}")


def run_verification():
    """
    Main function to verify all batch execution results.
    """
    print("\n" + "="*80)
    print("🔍 BATCH RESULTS VERIFICATION")
    print("="*80)
    
    # Load modifications
    print(f"\n📂 Loading modifications from: {MODIFICATIONS_FILE}")
    modifications = load_modifications()
    total_cases = len(modifications)
    print(f"✅ Found {total_cases} cases to verify")
    
    # Load batch results (optional, for reference)
    batch_results = load_batch_results()
    if batch_results:
        print(f"📊 Loaded batch execution results with {len(batch_results.get('results', []))} entries")
    
    # Initialize LLM
    print(f"\n🤖 Initializing LLM: {LLM_MODEL_NAME}")
    llm_instance = llm()
    
    # Track verification results
    verification_data = {
        "verification_start_time": datetime.now().isoformat(),
        "total_cases": total_cases,
        "modifications_file": MODIFICATIONS_FILE,
        "output_directory": OUTPUT_BASE_DIR,
        "results": []
    }
    
    passed_count = 0
    failed_count = 0
    partial_count = 0
    
    # Verify each case
    for index, modification in enumerate(modifications, start=1):
        result = verify_single_case(llm_instance, modification, index, total_cases)
        verification_data["results"].append(result)
        
        if result['status'] == 'passed':
            passed_count += 1
        elif result['status'] == 'failed':
            failed_count += 1
        elif result['status'] == 'partial':
            partial_count += 1
        
        # Update summary
        verification_data["current_summary"] = {
            "verified": index,
            "remaining": total_cases - index,
            "passed": passed_count,
            "failed": failed_count,
            "partial": partial_count
        }
        
        # Save intermediate results
        if index % 5 == 0 or index == total_cases:
            print(f"\n💾 Saving progress: {index}/{total_cases} cases verified...")
            save_verification_results(verification_data)
    
    # Finalize results
    verification_data["verification_end_time"] = datetime.now().isoformat()
    verification_data["summary"] = {
        "passed": passed_count,
        "failed": failed_count,
        "partial": partial_count,
        "success_rate": f"{(passed_count / total_cases * 100):.1f}%"
    }
    
    # Save final results
    save_verification_results(verification_data)
    
    # Print final summary
    print("\n" + "="*80)
    print("📊 VERIFICATION SUMMARY")
    print("="*80)
    print(f"✅ Passed: {passed_count}/{total_cases} ({passed_count / total_cases * 100:.1f}%)")
    print(f"❌ Failed: {failed_count}/{total_cases} ({failed_count / total_cases * 100:.1f}%)")
    print(f"⚠️  Partial: {partial_count}/{total_cases} ({partial_count / total_cases * 100:.1f}%)")
    print(f"\n📁 Results saved to: {VERIFICATION_RESULTS_FILE}")
    print("="*80 + "\n")
    
    return verification_data


if __name__ == '__main__':
    run_verification()
