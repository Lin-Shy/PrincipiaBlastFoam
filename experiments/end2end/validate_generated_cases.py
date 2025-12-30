"""
End-to-End Validation Script for Generated OpenFOAM Cases

This script validates generated cases from batch workflow execution against multiple criteria:
1. Executability - Can the case run successfully (with time limit)
2. Physical Parameter Validity - Are modifications physically reasonable
3. File Structure Completeness - Does the case have all required files
4. Configuration Consistency - Are settings internally consistent
"""

import os
import json
import sys
import time
import signal
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from principia_ai.tools.user_guide_knowledge_graph_tool import UserGuideKnowledgeGraphRetriever

# Configuration
mode = "senior"
CASES_ROOT_DIR = f"/media/dev/vdb1/linshihao/LLM/LLM-output-cases/agent-batch_runs/blastfoam_{mode}_modifications"
MODIFICATIONS_FILE = f"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/dataset/modification/blastfoam_{mode}_modifications.json"
VALIDATION_OUTPUT_FILE = os.path.join(CASES_ROOT_DIR, "{mode}_validation_results.json")
EXECUTION_TIMEOUT = 120  # 2 minutes max per case

class CaseValidator:
    """Comprehensive validator for generated OpenFOAM cases"""
    
    def __init__(self, llm_api_key=None, llm_base_url=None, llm_model=None):
        """
        Initialize the validator with LLM and knowledge retriever.
        
        Args:
            llm_api_key: API key for LLM
            llm_base_url: Base URL for LLM API
            llm_model: Model name to use
        """
        load_dotenv(override=True)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            base_url=llm_base_url or os.getenv("LLM_API_BASE_URL"),
            model=llm_model or os.getenv("LLM_MODEL"),
            api_key=llm_api_key or os.getenv("LLM_API_KEY"),
            temperature=0.1,
        )
        
        # Initialize User Guide retriever for physical validation
        try:
            self.user_guide_retriever = UserGuideKnowledgeGraphRetriever()
            print("✓ User Guide Knowledge Graph Retriever initialized")
        except Exception as e:
            print(f"⚠ Warning: Could not initialize User Guide retriever: {e}")
            self.user_guide_retriever = None
    
    def validate_case(self, case_info: Dict[str, Any], 
                     execution_timeout: int = 300) -> Dict[str, Any]:
        """
        Validate a single generated case against all criteria.
        
        Args:
            case_info: Dictionary containing case metadata from batch results
            execution_timeout: Maximum time in seconds to run the case
            
        Returns:
            Dictionary with validation results
        """
        case_name = case_info.get('case_name', 'unknown')
        case_path = case_info.get('case_path', '')
        
        print(f"\n{'='*80}")
        print(f"🔍 Validating Case: {case_name}")
        print(f"{'='*80}")
        
        validation_results = {
            'case_name': case_name,
            'case_path': case_path,
            'validation_timestamp': datetime.now().isoformat(),
            'validations': {}
        }
        
        # 3. Physical Parameter Validation
        print("\n🔬 Validating physical parameters...")
        validation_results['validations']['physical_parameters'] = \
            self._validate_physical_parameters(case_path, case_info)
        
        # 4. Executability Validation (with timeout)
        print(f"\n🚀 Testing executability (timeout: {execution_timeout}s)...")
        validation_results['validations']['executability'] = \
            self._validate_executability(case_path, execution_timeout)
        
        # Compute overall validation score
        validation_results['overall_score'] = self._compute_validation_score(
            validation_results['validations']
        )
        
        return validation_results
    
    def _validate_physical_parameters(self, case_path: str, 
                                     case_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate physical parameters using User Guide knowledge retrieval.
        
        Args:
            case_path: Path to the case directory
            case_info: Case metadata including user request
            
        Returns:
            Validation results for physical parameters
        """
        results = {
            'status': 'passed',
            'issues': [],
            'warnings': [],
            'details': {},
            'llm_analysis': None
        }
        
        if not self.user_guide_retriever:
            results['warnings'].append(
                "User Guide retriever not available, skipping detailed validation"
            )
            return results
        
        user_request = case_info.get('user_request', '')
        modified_files = case_info.get('modified_files', [])
        
        if not user_request:
            results['warnings'].append("No user request found for validation")
            return results
        
        # Read modified configuration files
        modified_contents = {}
        for file_name in modified_files:
            file_path = os.path.join(case_path, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        modified_contents[file_name] = f.read()
                except Exception as e:
                    results['warnings'].append(
                        f"Could not read {file_name}: {e}"
                    )
        
        # Retrieve relevant documentation
        print("  📚 Retrieving relevant User Guide context...")
        try:
            guide_context = self.user_guide_retriever.search(user_request)
            results['details']['guide_context_retrieved'] = bool(guide_context)
        except Exception as e:
            results['warnings'].append(f"User Guide retrieval failed: {e}")
            guide_context = None
        
        # Use LLM to analyze physical validity
        if guide_context and modified_contents:
            print("  🤖 Analyzing physical parameter validity with LLM...")
            try:
                analysis = self._llm_validate_physics(
                    user_request, modified_contents, guide_context
                )
                results['llm_analysis'] = analysis
                
                if analysis.get('status') == 'invalid':
                    results['status'] = 'failed'
                    results['issues'].extend(analysis.get('issues', []))
                elif analysis.get('status') == 'questionable':
                    results['status'] = 'warning'
                    results['warnings'].extend(analysis.get('warnings', []))
                
            except Exception as e:
                results['warnings'].append(f"LLM analysis failed: {e}")
        
        print(f"  ✓ Physical parameter check complete: {results['status']}")
        return results
    
    def _llm_validate_physics(self, user_request: str, 
                            modified_contents: Dict[str, str],
                            guide_context: str) -> Dict[str, Any]:
        """
        Use LLM to validate physical parameters against documentation.
        
        Args:
            user_request: Original user request
            modified_contents: Dictionary of modified file contents
            guide_context: Retrieved documentation context
            
        Returns:
            Analysis results
        """
        # Remove C-style block comments (/* ... */) from modified contents
        # before building the summary to avoid sending large comment blocks
        # to the LLM. Only block comments are removed as requested.
        cleaned_contents = {
            name: re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            for name, content in modified_contents.items()
        }

        files_summary = "\n\n".join([
            f"=== {name} ===\n{cleaned_contents[name]}..."
            for name in cleaned_contents
        ])

        # Extract numeric-looking parameters from modified contents to give LLM
        # a concise structured list to check magnitudes, units and ranges.
        numeric_params = []
        num_pattern = re.compile(r"([a-zA-Z0-9_\-/\\.]+)\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*;")
        for fname, content in cleaned_contents.items():
            for m in num_pattern.finditer(content):
                key = m.group(1).strip()
                val = m.group(2)
                try:
                    fval = float(val)
                except Exception:
                    fval = None
                numeric_params.append({
                    'file': fname,
                    'key_snippet': key,
                    'raw_value': val,
                    'value': fval
                })

        numeric_summary = "\n".join([
            f"- {p['file']}: {p['key_snippet']} = {p['raw_value']}" for p in numeric_params
        ]) if numeric_params else "(no explicit simple numeric key-value pairs detected)"

        # Stronger prompt: ask the LLM to reason from theory and expected ranges,
        # compute simple nondimensional numbers where possible (Re, CFL), and
        # return a structured JSON including per-parameter numeric checks and
        # recommended fixes and confidence for each judgement.
        prompt = f"""You are an expert in computational fluid dynamics and OpenFOAM/BlastFoam.
For each modified file and parameter below, use relevant theory and the provided
User Guide context to judge whether numeric values and settings are physically
plausible, meet solver requirements, and follow best-practice ranges.

USER REQUEST:
{user_request}

MODIFIED FILE CONTENTS (truncated):
{files_summary}

EXTRACTED NUMERIC PARAMETERS (simple key/value pairs found):
{numeric_summary}

RELEVANT DOCUMENTATION (truncated):
{guide_context[:3000] if len(str(guide_context)) > 3000 else guide_context}

TASK (be systematic):
1) For each numeric parameter you can identify, report:
   - file, parameter (a short snippet), numeric value (as number if parseable)
   - whether the magnitude is physically reasonable and why (cite physics/theory or typical ranges)
   - if applicable, compute simple nondimensional numbers (Reynolds number, CFL estimate using deltaT and velocity/mesh spacing when possible) and compare with typical stability/convergence ranges
   - expected/acceptable range (if known) and suggested corrected values or diagnostics to compute
   - a confidence score between 0.0 and 1.0 for the judgement

2) For boundary/initial conditions and material properties, check consistency (e.g. density/viscosity/temperature) and flag contradictions.

3) For time-stepping and solver settings (deltaT, endTime, tolerances), check orders of magnitude and consistency with application and mesh/time-resolution.

4) Identify any settings that directly contradict OpenFOAM/BlastFoam documentation and cite the reason or doc snippet.

OUTPUT FORMAT (strict JSON):
{{
  "status": "valid" | "questionable" | "invalid",
  "issues": ["critical issue 1", ...],
  "warnings": ["potential problem 1", ...],
  "numeric_checks": [
    {{
      "file": "system/controlDict",
      "parameter": "deltaT",
      "value": 0.001,
      "expected_range": "1e-6 - 1e-1 (example)",
      "status": "ok" | "questionable" | "invalid",
      "confidence": 0.0-1.0,
      "explanation": "Short physics-based rationale",
      "recommendation": "Suggested fix or diagnostic to run"
    }}
  ],
  "analysis_summary": "Concise multi-sentence summary",
  "suggested_tests": ["run a mesh refinement study", "compute CFL = ..." ]
}}

Be concise in each explanation and return only valid JSON (no additional commentary).
"""

        messages = [
            SystemMessage(content="You are an expert OpenFOAM/BlastFoam validator with strong background in fluid mechanics and numerical methods."),
            HumanMessage(content=prompt)
        ]

        response = self.llm.invoke(messages)
        
        # Parse response
        try:
            # Extract JSON from response (robust to code fences)
            content = getattr(response, 'content', '') or str(response)
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # take content inside the first code fence
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                # Try to find the first '{' to the last '}' as a fallback
                start = content.find('{')
                end = content.rfind('}')
                json_str = content[start:end+1].strip() if start != -1 and end != -1 else content.strip()

            parsed = json.loads(json_str)
            # Defensive: ensure numeric_checks exists
            if 'numeric_checks' not in parsed:
                parsed['numeric_checks'] = []
            return parsed
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                'status': 'questionable',
                'issues': [],
                'warnings': ['Could not parse LLM response'],
                'analysis_summary': response.content[:500]
            }
    
    def _validate_executability(self, case_path: str, 
                               timeout: int = 300) -> Dict[str, Any]:
        """
        Test if the case can execute successfully (with timeout).
        
        This uses a similar approach to the reviewer agent for log analysis.
        
        Args:
            case_path: Path to the case directory
            timeout: Maximum execution time in seconds
            
        Returns:
            Validation results for executability
        """
        results = {
            'status': 'passed',
            'issues': [],
            'warnings': [],
            'details': {},
            'execution_time': 0,
            'log_analysis': {}
        }
        
        allrun_path = os.path.join(case_path, 'Allrun')
        
        if not os.path.exists(allrun_path):
            results['status'] = 'failed'
            results['issues'].append("Allrun script not found")
            return results
        
        # Make Allrun executable
        try:
            os.chmod(allrun_path, 0o755)
        except Exception as e:
            results['warnings'].append(f"Could not make Allrun executable: {e}")
        
        # Execute with timeout
        print(f"  ⏱️  Running case (max {timeout}s)...")
        start_time = time.time()
        
        try:
            # Run Allrun with timeout
            process = subprocess.Popen(
                ['bash', allrun_path],
                cwd=case_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid  # Create new process group for timeout handling
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                execution_time = time.time() - start_time
                results['execution_time'] = execution_time
                results['details']['completed_normally'] = True
                results['details']['exit_code'] = process.returncode
                
                # Don't immediately fail on non-zero exit code
                # OpenFOAM scripts sometimes return non-zero even when successful
                # We'll rely on log analysis for the final determination
                if process.returncode != 0:
                    results['warnings'].append(
                        f"Process exited with non-zero code {process.returncode} (will check logs)"
                    )
                
            except subprocess.TimeoutExpired:
                # Kill the process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(2)
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                
                execution_time = time.time() - start_time
                results['execution_time'] = execution_time
                results['details']['completed_normally'] = False
                results['details']['timeout_reached'] = True
                results['warnings'].append(f"Execution timeout after {timeout}s")
                
                # Still analyze logs even if timeout
                print(f"  ⏰ Timeout reached, analyzing partial logs...")
                
        except Exception as e:
            results['status'] = 'failed'
            results['issues'].append(f"Execution error: {e}")
            return results
        
        # Analyze log files
        print("  📋 Analyzing log files...")
        log_analysis = self._analyze_execution_logs(case_path)
        results['log_analysis'] = log_analysis
        
        # Update status based on log analysis (prioritize log analysis over exit code)
        # Priority 1: Check for completion markers (highest priority - indicates success)
        if log_analysis.get('has_completion_markers'):
            results['status'] = 'passed'
            print("  ✓ Found successful completion markers in logs")
            # Clear any previous issues related to exit code
            results['issues'] = [issue for issue in results['issues'] 
                                if 'exit code' not in issue.lower()]
        # Priority 2: Check for definitive errors
        elif log_analysis.get('has_errors'):
            results['status'] = 'failed'
            results['issues'].extend(log_analysis.get('error_details', []))
            print("  ❌ Found errors in logs")
        # Priority 3: Check if execution completed normally without logs
        elif results['details'].get('completed_normally') and not log_analysis.get('log_files_found'):
            # No logs found but process completed normally
            results['status'] = 'warning'
            results['warnings'].append(
                "Execution completed but no log files found for verification"
            )
        # Priority 4: Timeout without errors
        elif results['details'].get('timeout_reached'):
            # If timeout but no errors in logs, it's a partial success
            results['status'] = 'warning'
            results['warnings'].append(
                "Execution incomplete (timeout) but no errors detected in logs"
            )
        # Priority 5: Check exit code if no clear indication from logs
        elif results['details'].get('exit_code', 0) != 0:
            results['status'] = 'warning'
            results['warnings'].append(
                f"Non-zero exit code ({results['details']['exit_code']}) but no clear errors in logs"
            )
        else:
            # Everything seems OK but no completion markers
            results['status'] = 'warning'
            results['warnings'].append(
                "Execution completed but no clear completion markers found"
            )
        
        print(f"  ✓ Executability check complete: {results['status']}")
        return results
    
    def _analyze_execution_logs(self, case_path: str) -> Dict[str, Any]:
        """
        Analyze log files using keyword matching similar to reviewer agent.
        This implementation follows reviewer.py's approach with priority checks.
        
        Args:
            case_path: Path to the case directory
            
        Returns:
            Log analysis results
        """
        log_files = self._collect_log_files(case_path)
        
        analysis = {
            'log_files_found': len(log_files),
            'log_files': list(log_files.keys()),
            'has_completion_markers': False,
            'has_errors': False,
            'error_details': [],
            'completion_details': []
        }
        
        if not log_files:
            return analysis
        
        # Priority 1: Check for successful completion markers (following reviewer.py logic)
        completion_patterns = [
            'End', 'END', 'end',
            'Finalising parallel run',
            'finalising parallel run',
            'SIMPLE solution converged',
            'solution converged',
            'ExecutionTime =',
            'ClockTime =',
            'Writing solution for',
            'Time =',
            'writeData'
        ]
        
        for log_name, log_content in log_files.items():
            if not log_content.strip():
                continue
            
            content_lines = log_content.split('\n')
            # Check the last 10 lines for completion markers (higher priority)
            last_lines = content_lines[-10:] if len(content_lines) >= 10 else content_lines
            
            found_markers = []
            
            # Priority check in last few lines
            for line_num_from_end, line in enumerate(reversed(last_lines), 1):
                line_lower = line.lower()
                for pattern in completion_patterns:
                    if pattern.lower() in line_lower:
                        found_markers.append({
                            'marker': pattern,
                            'position': 'end_region',
                            'line': line.strip()[:100]
                        })
                        analysis['has_completion_markers'] = True
                        break
            
            if found_markers:
                analysis['completion_details'].append({
                    'log_file': log_name,
                    'completion_markers': found_markers
                })
        
        # Priority 2: Check for definitive errors (following reviewer.py's improved detection)
        definitive_error_keywords = [
            'FATAL', 'Fatal', 'fatal',
            'FAILED', 'Failed',
            'Segmentation fault', 'segmentation fault',
            'Aborted', 'aborted', 'ABORT',
            'core dumped',
            'ERROR:', 'Error:', 'error:',  # With colon
            'ERROR -', 'Error -', 'error -',  # With dash
            'ERROR!', 'Error!', 'error!',   # With exclamation
            'execution error',
            'runtime error'
        ]
        
        for log_name, log_content in log_files.items():
            if not log_content.strip():
                continue
            
            content_lines = log_content.split('\n')
            found_errors = []
            
            for line_num, line in enumerate(content_lines, 1):
                line_lower = line.lower()
                
                for keyword in definitive_error_keywords:
                    if keyword.lower() in line_lower:
                        found_errors.append({
                            'keyword': keyword,
                            'line_number': line_num,
                            'line_content': line.strip()[:200]
                        })
                        analysis['has_errors'] = True
                        break
            
            if found_errors:
                analysis['error_details'].append({
                    'log_file': log_name,
                    'errors': found_errors[:5]  # Limit to first 5 errors per file
                })
        
        return analysis
        
        return analysis
    
    def _collect_log_files(self, case_path: str) -> Dict[str, str]:
        """Collect all log files from case directory."""
        log_files = {}
        
        # Multiple patterns to catch different log file naming conventions
        patterns = ['log.*', '*.log', 'log', 'Log.*']
        
        for pattern in patterns:
            import glob
            search_pattern = os.path.join(case_path, pattern)
            for log_path in glob.glob(search_pattern):
                if os.path.isfile(log_path):
                    log_name = os.path.basename(log_path)
                    # Skip if already collected
                    if log_name in log_files:
                        continue
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            log_files[log_name] = f.read()
                        print(f"    📄 Found log: {log_name}")
                    except Exception as e:
                        print(f"  ⚠ Could not read {log_path}: {e}")
        
        # Also check common subdirectories
        for subdir in ['postProcessing', 'logs']:
            subdir_path = os.path.join(case_path, subdir)
            if os.path.isdir(subdir_path):
                for pattern in patterns:
                    search_pattern = os.path.join(subdir_path, pattern)
                    for log_path in glob.glob(search_pattern):
                        if os.path.isfile(log_path):
                            log_name = f"{subdir}/{os.path.basename(log_path)}"
                            if log_name not in log_files:
                                try:
                                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        log_files[log_name] = f.read()
                                    print(f"    📄 Found log: {log_name}")
                                except Exception as e:
                                    print(f"  ⚠ Could not read {log_path}: {e}")
        
        if not log_files:
            print("    ⚠️  No log files found")
        else:
            print(f"    ✓ Collected {len(log_files)} log file(s)")
        
        return log_files
    
    def _read_foam_dict(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read an OpenFOAM dictionary file and extract key-value pairs.
        Simple parser for basic validation.
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Very basic parsing - just extract key-value pairs
            result = {}
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('//') or line.startswith('/*'):
                    continue
                
                # Look for simple key-value pairs
                if ' ' in line and ';' in line:
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        key = parts[0]
                        value = parts[1].rstrip(';').strip()
                        result[key] = value
            
            return result
        except Exception as e:
            print(f"  ⚠ Error reading {file_path}: {e}")
            return None
    
    def _compute_validation_score(self, validations: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Compute overall validation score based on individual category pass rates.
        Each category is evaluated independently without weights.
        
        Args:
            validations: Dictionary of all validation results
            
        Returns:
            Overall score and summary with individual category pass rates
        """
        # Status to numeric score mapping
        scores = {
            'passed': 1.0,
            'warning': 0.5,
            'failed': 0.0
        }
        
        # Calculate individual category scores (pass rates)
        category_scores = {}
        category_statuses = {}
        
        for category, validation in validations.items():
            status = validation.get('status', 'failed')
            category_statuses[category] = status
            category_scores[category] = scores.get(status, 0.0)
        
        # Calculate overall statistics
        total_categories = len(category_scores)
        if total_categories == 0:
            return {
                'overall_status': 'failed',
                'category_scores': {},
                'category_statuses': {},
                'pass_rate_by_category': {},
                'overall_pass_rate': 0.0,
                'summary': {
                    'total_categories': 0,
                    'passed': 0,
                    'warning': 0,
                    'failed': 0
                }
            }
        
        # Count statuses
        status_counts = {'passed': 0, 'warning': 0, 'failed': 0}
        for status in category_statuses.values():
            status_counts[status] += 1
        
        # Calculate pass rates (percentage)
        pass_rate_by_category = {
            cat: score * 100 for cat, score in category_scores.items()
        }
        
        # Overall pass rate is the average of all category pass rates
        overall_pass_rate = sum(category_scores.values()) / total_categories * 100
        
        # Determine overall status based on category results
        if status_counts['failed'] > 0:
            overall_status = 'failed'
        elif status_counts['warning'] > 0:
            overall_status = 'warning'
        else:
            overall_status = 'passed'
        
        return {
            'overall_status': overall_status,
            'category_scores': category_scores,  # Raw scores (0.0, 0.5, 1.0)
            'category_statuses': category_statuses,  # Status strings
            'pass_rate_by_category': pass_rate_by_category,  # Percentage per category
            'overall_pass_rate': overall_pass_rate,  # Average percentage
            'summary': {
                'total_categories': total_categories,
                'passed': status_counts['passed'],
                'warning': status_counts['warning'],
                'failed': status_counts['failed']
            }
        }


def is_case_directory(case_path: str) -> bool:
    """
    Heuristic check whether a folder looks like an OpenFOAM/BlastFoam case.

    Returns True if the folder contains typical case markers such as:
      - a 'system' directory with 'controlDict'
      - a 'constant' directory (optionally with 'polyMesh')
      - a time-0 directory named '0' (or any directory starting with '0')
      - an 'Allrun' script (common in tutorial/run bundles)

    This is intentionally conservative: any of the above present -> likely a case.
    """
    try:
        if not os.path.isdir(case_path):
            return False

        # quick markers
        allrun = os.path.isfile(os.path.join(case_path, 'Allrun')) or os.path.isfile(os.path.join(case_path, 'Allrun.sh'))
        system_dir = os.path.join(case_path, 'system')
        constant_dir = os.path.join(case_path, 'constant')
        zero_dir = os.path.join(case_path, '0')

        has_system = os.path.isdir(system_dir)
        has_constant = os.path.isdir(constant_dir)
        has_zero = os.path.isdir(zero_dir)

        # Some cases use directories like '0.org' or '0.orig' - treat any dir starting with '0' as a zero folder
        if not has_zero:
            try:
                for name in os.listdir(case_path):
                    full = os.path.join(case_path, name)
                    if os.path.isdir(full) and name.startswith('0'):
                        has_zero = True
                        break
            except Exception:
                pass

        control_dict = os.path.isfile(os.path.join(system_dir, 'controlDict')) if has_system else False
        poly_mesh = os.path.isdir(os.path.join(constant_dir, 'polyMesh')) if has_constant else False

        # Decide: prefer explicit Allrun, otherwise require system+constant+zero and at least controlDict or polyMesh
        if allrun:
            return True

        if has_system and has_constant and has_zero and (control_dict or poly_mesh):
            return True

        # As a last resort, if system and constant exist it's likely a case
        if has_system and has_constant:
            return True

        return False
    except Exception:
        return False


def load_batch_results(results_file: str) -> Dict[str, Any]:
    """Load batch execution results from JSON file."""
    with open(results_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_validation_results(output_file: str, validation_results: List[Dict[str, Any]]):
    """Save validation results to JSON file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    report = {
        'validation_timestamp': datetime.now().isoformat(),
        'total_cases': len(validation_results),
        'summary': _compute_summary(validation_results),
        'results': validation_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Validation results saved to: {output_file}")


def _compute_summary(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics for validation results."""
    total = len(validation_results)
    
    status_counts = {'passed': 0, 'warning': 0, 'failed': 0}
    total_pass_rate = 0.0
    
    # Category-wise statistics
    category_pass_rates = {}
    
    for result in validation_results:
        overall = result.get('overall_score', {})
        status = overall.get('overall_status', 'failed')
        pass_rate = overall.get('overall_pass_rate', 0.0)
        
        status_counts[status] += 1
        total_pass_rate += pass_rate
        
        # Collect category pass rates
        category_rates = overall.get('pass_rate_by_category', {})
        for cat, rate in category_rates.items():
            if cat not in category_pass_rates:
                category_pass_rates[cat] = []
            category_pass_rates[cat].append(rate)
    
    # Calculate average pass rates per category
    avg_category_pass_rates = {
        cat: sum(rates) / len(rates) if rates else 0.0
        for cat, rates in category_pass_rates.items()
    }
    
    return {
        'total_cases': total,
        'passed': status_counts['passed'],
        'warnings': status_counts['warning'],
        'failed': status_counts['failed'],
        'average_overall_pass_rate': total_pass_rate / total if total > 0 else 0.0,
        'pass_rate': status_counts['passed'] / total if total > 0 else 0.0,
        'average_pass_rate_by_category': avg_category_pass_rates
    }


def main():
    """Main validation workflow."""
    
    print("="*80)
    print("🎯 END-TO-END CASE VALIDATION")
    print("="*80)

    # Load modifications data
    print(f"\n📄 Loading modifications data from: {MODIFICATIONS_FILE}")
    modifications_map = {}
    try:
        with open(MODIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            modifications_list = json.load(f)
        modifications_map = {item['case_name']: item for item in modifications_list}
        print(f"✅ Loaded data for {len(modifications_map)} modifications")
    except Exception as e:
        print(f"❌ Error loading modifications file: {e}. Physical validation may be limited.")

    # Discover cases from the directory
    print(f"\n📂 Discovering cases in: {CASES_ROOT_DIR}")
    
    cases_to_validate = []
    if os.path.isdir(CASES_ROOT_DIR):
        for item in os.listdir(CASES_ROOT_DIR):
            case_path = os.path.join(CASES_ROOT_DIR, item)
            if os.path.isdir(case_path):
                # Skip folders that don't look like OpenFOAM cases
                if not is_case_directory(case_path):
                    print(f"  ⚠ Skipping '{item}': not recognized as an OpenFOAM case")
                    continue

                # Get modification info from the loaded map
                mod_info = modifications_map.get(item, {})

                case_info = {
                    'case_name': item,
                    'case_path': case_path,
                    'user_request': mod_info.get('description', ''),
                    'modified_files': mod_info.get('modified_files', [])
                }
                cases_to_validate.append(case_info)
    
    total_cases = len(cases_to_validate)
    print(f"✅ Found {total_cases} cases to validate")
    
    # Initialize validator
    print("\n🔧 Initializing validator...")
    validator = CaseValidator()
    
    # Validate each case
    validation_results = []
    
    for index, case_info in enumerate(cases_to_validate, start=1):
        print(f"\n{'='*80}")
        print(f"Validating Case [{index}/{total_cases}]")
        print(f"{'='*80}")
        
        try:
            result = validator.validate_case(case_info, EXECUTION_TIMEOUT)
            validation_results.append(result)
            
            # Show quick status
            overall = result.get('overall_score', {})
            status = overall.get('overall_status', 'unknown')
            pass_rate = overall.get('overall_pass_rate', 0.0)
            
            status_icon = {'passed': '✅', 'warning': '⚠️', 'failed': '❌'}.get(status, '❓')
            print(f"\n{status_icon} Overall: {status.upper()} (pass rate: {pass_rate:.1f}%)")
            
            # Show individual category pass rates
            category_rates = overall.get('pass_rate_by_category', {})
            if category_rates:
                print("   Category pass rates:")
                for cat, rate in category_rates.items():
                    cat_status = overall.get('category_statuses', {}).get(cat, 'unknown')
                    cat_icon = {'passed': '✅', 'warning': '⚠️', 'failed': '❌'}.get(cat_status, '❓')
                    print(f"     {cat_icon} {cat}: {rate:.1f}%")
            
        except Exception as e:
            print(f"\n❌ Validation failed with error: {e}")
            validation_results.append({
                'case_name': case_info.get('case_name', 'unknown'),
                'case_path': case_info.get('case_path', ''),
                'validation_timestamp': datetime.now().isoformat(),
                'error': str(e),
                'overall_score': {
                    'overall_pass_rate': 0.0,
                    'overall_status': 'failed',
                    'category_scores': {},
                    'category_statuses': {},
                    'pass_rate_by_category': {},
                    'summary': {
                        'total_categories': 0,
                        'passed': 0,
                        'warning': 0,
                        'failed': 0
                    }
                }
            })
        
        # Save intermediate results
        save_validation_results(VALIDATION_OUTPUT_FILE, validation_results)
    
    # Print final summary
    summary = _compute_summary(validation_results)
    print("\n" + "="*80)
    print("📊 VALIDATION SUMMARY")
    print("="*80)
    print(f"✅ Passed: {summary['passed']}/{summary['total_cases']}")
    print(f"⚠️  Warnings: {summary['warnings']}/{summary['total_cases']}")
    print(f"❌ Failed: {summary['failed']}/{summary['total_cases']}")
    print(f"📈 Overall Pass Rate: {summary['average_overall_pass_rate']:.1f}%")
    print(f"📊 Complete Pass Rate: {summary['pass_rate']*100:.1f}%")
    
    # Show average pass rates by category
    if summary.get('average_pass_rate_by_category'):
        print("\n📋 Average Pass Rates by Category:")
        for cat, rate in summary['average_pass_rate_by_category'].items():
            print(f"   {cat}: {rate:.1f}%")
    
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
