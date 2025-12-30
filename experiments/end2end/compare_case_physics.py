"""
Comparison Script for Physical Validity of Generated OpenFOAM Cases

This script compares two sets of generated cases (from different methods/configurations)
and evaluates which has better physical parameter validity using LLM analysis.

Usage:
    python compare_case_physics.py --dir-a /path/to/cases_a --dir-b /path/to/cases_b
"""

import os
import sys
import json
import re
import glob
import argparse
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

# ============================================================================
# CONFIGURATION - Modify these variables for your comparison
# ============================================================================
mode = "basic"
# Directory paths
CASES_DIR_A = f"/media/dev/vdb1/linshihao/LLM/LLM-output-cases/batch_runs/blastfoam_{mode}_modifications"
CASES_DIR_B = f"/media/dev/vdb1/linshihao/LLM/LLM-output-cases/no_kg-batch_runs/blastfoam_{mode}_modifications"

# Modifications metadata files (optional, for enhanced context)
MODIFICATIONS_FILE_A = f"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/dataset/modification/blastfoam_{mode}_modifications.json"
MODIFICATIONS_FILE_B = f"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/dataset/modification/blastfoam_{mode}_modifications.json"

# Output file for comparison results
OUTPUT_FILE = f"/media/dev/vdb1/linshihao/LLM/LLM-output-cases/{mode}_physics_comparison_results.json"

# LLM Configuration (leave None to use environment variables from .env)
LLM_API_KEY = "sk-4f9c1cbdc4ce43a7886791887284e108"
LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL = "qwen-plus"  # or set your model name

# File content truncation settings (to avoid excessive token usage)
MAX_FILE_CONTENT_LENGTH = 2000  # Max characters per file to send to LLM
MAX_GUIDE_CONTEXT_LENGTH = 3000  # Max characters of guide context to send to LLM

# ============================================================================
# END CONFIGURATION
# ============================================================================


class PhysicsComparator:
    """Compare physical validity between two sets of generated cases"""
    
    def __init__(self, llm_api_key=None, llm_base_url=None, llm_model=None):
        """
        Initialize the comparator with LLM and knowledge retriever.
        
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
    
    def compare_cases(self, case_a_info: Dict[str, Any], 
                     case_b_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare physical validity between two cases for the same modification request.
        
        Args:
            case_a_info: Case metadata from source A
            case_b_info: Case metadata from source B
            
        Returns:
            Dictionary with comparison results including preference
        """
        case_name = case_a_info.get('case_name', 'unknown')
        
        print(f"\n{'='*80}")
        print(f"🔍 Comparing Cases: {case_name}")
        print(f"{'='*80}")
        
        # Debug: Print case info
        print(f"📝 Case A info: path={case_a_info.get('case_path', '')}")
        print(f"   - user_request: {case_a_info.get('user_request', '')[:100] if case_a_info.get('user_request') else '(empty)'}")
        print(f"   - modified_files: {case_a_info.get('modified_files', [])}")
        print(f"📝 Case B info: path={case_b_info.get('case_path', '')}")
        print(f"   - user_request: {case_b_info.get('user_request', '')[:100] if case_b_info.get('user_request') else '(empty)'}")
        print(f"   - modified_files: {case_b_info.get('modified_files', [])}")
        
        comparison_result = {
            'case_name': case_name,
            'timestamp': datetime.now().isoformat(),
            'case_a_path': case_a_info.get('case_path', ''),
            'case_b_path': case_b_info.get('case_path', ''),
            'user_request': case_a_info.get('user_request', ''),
            'preference': None,  # 'A', 'B', or 'equal'
            'confidence': 0.0,
            'analysis': {}
        }
        
        # Read file contents from both cases
        print("\n📋 Reading files from Case A...")
        files_a = self._read_case_files(
            case_a_info.get('case_path', ''),
            case_a_info.get('modified_files', [])
        )
        
        print("\n📋 Reading files from Case B...")
        files_b = self._read_case_files(
            case_b_info.get('case_path', ''),
            case_b_info.get('modified_files', [])
        )
        
        # Retrieve relevant documentation
        user_request = case_a_info.get('user_request', '')
        guide_context = None
        
        if self.user_guide_retriever and user_request:
            print("\n📚 Retrieving relevant User Guide context...")
            try:
                guide_context = self.user_guide_retriever.search(user_request)
            except Exception as e:
                print(f"⚠ Warning: User Guide retrieval failed: {e}")
        
        # Use LLM to compare physical validity
        if files_a or files_b:
            print("\n🤖 Comparing physical validity with LLM...")
            try:
                comparison = self._llm_compare_physics(
                    user_request,
                    files_a,
                    files_b,
                    guide_context
                )
                
                comparison_result['preference'] = comparison.get('preference', 'equal')
                comparison_result['confidence'] = comparison.get('confidence', 0.0)
                comparison_result['analysis'] = comparison
                
            except Exception as e:
                print(f"❌ LLM comparison failed: {e}")
                comparison_result['analysis']['error'] = str(e)
        else:
            print("⚠ No file contents found in either case")
        
        # Print summary
        preference = comparison_result['preference']
        confidence = comparison_result['confidence']
        preference_icon = {'A': '🅰️', 'B': '🅱️', 'equal': '⚖️'}.get(preference, '❓')
        
        print(f"\n{preference_icon} Preference: {preference} (confidence: {confidence:.2f})")
        
        return comparison_result
    
    def _read_case_files(self, case_path: str, 
                        modified_files: List[str]) -> Dict[str, str]:
        """
        Read all file contents from a case without parameter extraction.
        
        This method directly reads the full contents of modified files,
        allowing the LLM to analyze the complete context rather than
        pre-extracted numeric parameters.
        
        Args:
            case_path: Path to the case directory
            modified_files: List of modified file names
            
        Returns:
            Dictionary mapping file names to their full contents
        """
        file_contents = {}
        
        # Read modified configuration files
        for file_name in modified_files:
            file_path = os.path.join(case_path, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_contents[file_name] = content
                        print(f"  ✓ Read {file_name} ({len(content)} chars)")
                except Exception as e:
                    print(f"  ⚠ Could not read {file_name}: {e}")
        
        return file_contents
    
    def _llm_compare_physics(self, user_request: str,
                            files_a: Dict[str, str],
                            files_b: Dict[str, str],
                            guide_context: Optional[str]) -> Dict[str, Any]:
        """
        Use LLM to compare physical validity between two cases.
        
        Args:
            user_request: Original user request
            files_a: File contents from case A
            files_b: File contents from case B
            guide_context: Retrieved documentation context
            
        Returns:
            Comparison analysis with preference
        """
        # Build summaries for both cases
        def build_summary(file_contents: Dict[str, str], label: str) -> str:
            if not file_contents:
                return f"{label}:\n(No files available)"
            
            # Remove C-style block comments to reduce noise
            cleaned = {
                name: re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                for name, content in file_contents.items()
            }
            
            # Build file summary with full or truncated content
            files_summary = "\n\n".join([
                f"=== {name} ===\n{cleaned[name][:MAX_FILE_CONTENT_LENGTH]}{'...' if len(cleaned[name]) > MAX_FILE_CONTENT_LENGTH else ''}"
                for name in sorted(cleaned.keys())
            ])
            
            return f"""
{label}:
{files_summary}
"""
        
        summary_a = build_summary(files_a, "CASE A")
        summary_b = build_summary(files_b, "CASE B")
        
        # Construct comparison prompt
        prompt = f"""You are an expert in computational fluid dynamics and OpenFOAM/BlastFoam.

You are comparing two different implementations of the same modification request.
Both cases attempted to satisfy the user's request but may have different parameter choices.

Your task is to determine which case has BETTER physical validity and parameter choices.

USER REQUEST:
{user_request}

{summary_a}

{summary_b}

RELEVANT DOCUMENTATION (truncated):
{guide_context[:MAX_GUIDE_CONTEXT_LENGTH] if guide_context and len(str(guide_context)) > MAX_GUIDE_CONTEXT_LENGTH else (guide_context or "No documentation available")}

EVALUATION CRITERIA (in order of importance):
1. **Physical Correctness**: Which case has more physically reasonable values?
   - Are magnitudes appropriate for the physics?
   - Are units and dimensions correct?
   - Do parameters follow theoretical constraints?
   
2. **Consistency with Documentation**: Which case better follows OpenFOAM/BlastFoam best practices?
   - Are recommended ranges respected?
   - Are solver-specific requirements met?
   
3. **Internal Consistency**: Which case has better consistency between related parameters?
   - Do boundary conditions match initial conditions?
   - Are material properties consistent?
   - Is time-stepping appropriate for the mesh/physics?
   
4. **Numerical Stability**: Which case is more likely to produce stable, convergent solutions?
   - CFL condition considerations
   - Time step size appropriateness
   - Solver tolerance settings

OUTPUT FORMAT (strict JSON):
{{
  "preference": "A" | "B" | "equal",
  "confidence": 0.0-1.0,
  "reasoning": "Detailed explanation of why one case is preferred (2-4 sentences)",
  "case_a_strengths": ["strength 1", "strength 2", ...],
  "case_a_weaknesses": ["weakness 1", "weakness 2", ...],
  "case_b_strengths": ["strength 1", "strength 2", ...],
  "case_b_weaknesses": ["weakness 1", "weakness 2", ...],
  "key_differences": [
    {{
      "parameter": "parameter name",
      "case_a_value": "value in A",
      "case_b_value": "value in B",
      "preferred": "A" | "B" | "equal",
      "explanation": "why this value is better/worse"
    }}
  ],
  "overall_assessment": "Concise summary (1-2 sentences)"
}}

IMPORTANT:
- If both cases are equally valid, set preference to "equal"
- Confidence should reflect how clear the preference is (1.0 = very clear, 0.0 = cannot decide)
- Focus on PHYSICAL and NUMERICAL correctness, not code style
- Return ONLY valid JSON, no additional commentary

"""
        
        messages = [
            SystemMessage(content="You are an expert OpenFOAM/BlastFoam validator with deep knowledge of CFD physics and numerical methods."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Parse response
        try:
            content = getattr(response, 'content', '') or str(response)
            
            # Extract JSON from response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                start = content.find('{')
                end = content.rfind('}')
                json_str = content[start:end+1].strip() if start != -1 and end != -1 else content.strip()
            
            parsed = json.loads(json_str)
            
            # Validate required fields
            if 'preference' not in parsed:
                parsed['preference'] = 'equal'
            if 'confidence' not in parsed:
                parsed['confidence'] = 0.0
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"⚠ Warning: Could not parse LLM response: {e}")
            return {
                'preference': 'equal',
                'confidence': 0.0,
                'reasoning': 'Failed to parse LLM response',
                'raw_response': response.content[:500]
            }


def is_case_directory(case_path: str) -> bool:
    """
    Heuristic check whether a folder looks like an OpenFOAM/BlastFoam case.
    """
    try:
        if not os.path.isdir(case_path):
            return False

        allrun = os.path.isfile(os.path.join(case_path, 'Allrun')) or \
                 os.path.isfile(os.path.join(case_path, 'Allrun.sh'))
        system_dir = os.path.join(case_path, 'system')
        constant_dir = os.path.join(case_path, 'constant')
        zero_dir = os.path.join(case_path, '0')

        has_system = os.path.isdir(system_dir)
        has_constant = os.path.isdir(constant_dir)
        has_zero = os.path.isdir(zero_dir)

        if not has_zero:
            try:
                items = os.listdir(case_path)
                has_zero = any(item.startswith('0') and os.path.isdir(os.path.join(case_path, item)) 
                              for item in items)
            except Exception:
                pass

        control_dict = os.path.isfile(os.path.join(system_dir, 'controlDict')) if has_system else False
        poly_mesh = os.path.isdir(os.path.join(constant_dir, 'polyMesh')) if has_constant else False

        if allrun:
            return True

        if has_system and has_constant and has_zero and (control_dict or poly_mesh):
            return True

        if has_system and has_constant:
            return True

        return False
    except Exception:
        return False


def discover_cases(root_dir: str, modifications_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover cases from a directory.
    
    Args:
        root_dir: Root directory to search for cases
        modifications_file: Optional JSON file with modification metadata
        
    Returns:
        List of case info dictionaries
    """
    cases = []
    
    # Load modifications metadata if available
    modifications_map = {}
    if modifications_file and os.path.exists(modifications_file):
        try:
            with open(modifications_file, 'r', encoding='utf-8') as f:
                modifications_list = json.load(f)
            modifications_map = {item['case_name']: item for item in modifications_list}
            print(f"✅ Loaded {len(modifications_map)} modification entries from {os.path.basename(modifications_file)}")
            # Debug: show first entry structure
            if modifications_map:
                first_key = list(modifications_map.keys())[0]
                print(f"📝 Sample entry keys: {list(modifications_map[first_key].keys())}")
        except Exception as e:
            print(f"⚠ Warning: Could not load modifications file: {e}")
    
    # Discover cases
    if os.path.isdir(root_dir):
        for item in os.listdir(root_dir):
            case_path = os.path.join(root_dir, item)
            if os.path.isdir(case_path) and is_case_directory(case_path):
                case_info = {
                    'case_name': item,
                    'case_path': case_path,
                    'user_request': '',
                    'modified_files': []
                }
                
                # Add metadata if available
                if item in modifications_map:
                    mod = modifications_map[item]
                    
                    # Build user_request from available fields
                    # Combine description and modification for full context
                    description = mod.get('description', '')
                    modification = mod.get('modification', '')
                    
                    if description and modification:
                        # Combine both for complete context
                        case_info['user_request'] = f"{description}\n\nModification: {modification}"
                    elif description:
                        case_info['user_request'] = description
                    elif modification:
                        case_info['user_request'] = modification
                    else:
                        # Fallback to other possible field names
                        case_info['user_request'] = (
                            mod.get('user_request') or 
                            mod.get('modification_request') or 
                            mod.get('request') or 
                            ''
                        )
                    
                    # Get modified files list
                    case_info['modified_files'] = (
                        mod.get('modified_files') or  # Primary field in the JSON
                        mod.get('files_to_modify') or 
                        mod.get('files') or 
                        mod.get('target_files') or 
                        []
                    )
                    
                    print(f"  ✓ Loaded metadata for '{item}':")
                    print(f"    - request length: {len(case_info['user_request'])} chars")
                    print(f"    - modified_files: {case_info['modified_files']}")
                else:
                    print(f"  ⚠ No metadata found for '{item}' in modifications file")
                
                cases.append(case_info)
    
    return cases


def save_comparison_results(output_file: str, comparison_results: List[Dict[str, Any]]):
    """Save comparison results to JSON file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Compute summary statistics
    total = len(comparison_results)
    preference_counts = {'A': 0, 'B': 0, 'equal': 0}
    total_confidence = 0.0
    
    for result in comparison_results:
        pref = result.get('preference', 'equal')
        if pref in preference_counts:
            preference_counts[pref] += 1
        total_confidence += result.get('confidence', 0.0)
    
    avg_confidence = total_confidence / total if total > 0 else 0.0
    
    report = {
        'comparison_timestamp': datetime.now().isoformat(),
        'total_comparisons': total,
        'summary': {
            'prefer_a': preference_counts['A'],
            'prefer_b': preference_counts['B'],
            'equal': preference_counts['equal'],
            'average_confidence': avg_confidence,
            'a_win_rate': preference_counts['A'] / total if total > 0 else 0.0,
            'b_win_rate': preference_counts['B'] / total if total > 0 else 0.0,
        },
        'results': comparison_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Comparison results saved to: {output_file}")


def main():
    """Main comparison workflow."""
    
    parser = argparse.ArgumentParser(
        description='Compare physical validity between two sets of generated OpenFOAM cases'
    )
    parser.add_argument(
        '--dir-a',
        default=CASES_DIR_A,
        help=f'Path to directory A (first set of cases). Default: {CASES_DIR_A}'
    )
    parser.add_argument(
        '--dir-b',
        default=CASES_DIR_B,
        help=f'Path to directory B (second set of cases). Default: {CASES_DIR_B}'
    )
    parser.add_argument(
        '--modifications-a',
        default=MODIFICATIONS_FILE_A,
        help=f'Path to modifications JSON file for directory A. Default: {MODIFICATIONS_FILE_A}'
    )
    parser.add_argument(
        '--modifications-b',
        default=MODIFICATIONS_FILE_B,
        help=f'Path to modifications JSON file for directory B. Default: {MODIFICATIONS_FILE_B}'
    )
    parser.add_argument(
        '--output',
        default=OUTPUT_FILE,
        help=f'Output file path for comparison results. Default: {OUTPUT_FILE}'
    )
    
    args = parser.parse_args()
    
    dir_a = args.dir_a
    dir_b = args.dir_b
    modifications_a = args.modifications_a
    modifications_b = args.modifications_b
    output_file = args.output
    
    print("="*80)
    print("🔬 PHYSICS COMPARISON: CASE A vs CASE B")
    print("="*80)
    print(f"Directory A: {dir_a}")
    print(f"Directory B: {dir_b}")
    print("="*80)
    
    # Discover cases from both directories
    print("\n📂 Discovering cases from Directory A...")
    cases_a = discover_cases(dir_a, modifications_a)
    print(f"✅ Found {len(cases_a)} cases in Directory A")
    
    print("\n📂 Discovering cases from Directory B...")
    cases_b = discover_cases(dir_b, modifications_b)
    print(f"✅ Found {len(cases_b)} cases in Directory B")
    
    # Match cases by name
    cases_a_map = {c['case_name']: c for c in cases_a}
    cases_b_map = {c['case_name']: c for c in cases_b}
    
    common_cases = set(cases_a_map.keys()) & set(cases_b_map.keys())
    
    if not common_cases:
        print("\n❌ No common cases found between directories!")
        print("Cases in A:", list(cases_a_map.keys())[:5], "...")
        print("Cases in B:", list(cases_b_map.keys())[:5], "...")
        return
    
    print(f"\n✅ Found {len(common_cases)} common cases to compare")
    
    # Initialize comparator
    print("\n🔧 Initializing physics comparator...")
    comparator = PhysicsComparator(
        llm_api_key=LLM_API_KEY,
        llm_base_url=LLM_BASE_URL,
        llm_model=LLM_MODEL
    )
    
    # Compare each pair of cases
    comparison_results = []
    
    for index, case_name in enumerate(sorted(common_cases), start=1):
        print(f"\n{'='*80}")
        print(f"Comparison [{index}/{len(common_cases)}]")
        print(f"{'='*80}")
        
        try:
            result = comparator.compare_cases(
                cases_a_map[case_name],
                cases_b_map[case_name]
            )
            comparison_results.append(result)
            
            # Save intermediate results
            save_comparison_results(output_file, comparison_results)
            
        except Exception as e:
            print(f"\n❌ Comparison failed with error: {e}")
            comparison_results.append({
                'case_name': case_name,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'preference': 'equal',
                'confidence': 0.0
            })
    
    # Print final summary
    total = len(comparison_results)
    preference_counts = {'A': 0, 'B': 0, 'equal': 0}
    total_confidence = 0.0
    
    for result in comparison_results:
        pref = result.get('preference', 'equal')
        if pref in preference_counts:
            preference_counts[pref] += 1
        total_confidence += result.get('confidence', 0.0)
    
    avg_confidence = total_confidence / total if total > 0 else 0.0
    
    print("\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    print(f"Total Comparisons: {total}")
    print(f"🅰️  Prefer A: {preference_counts['A']} ({preference_counts['A']/total*100:.1f}%)")
    print(f"🅱️  Prefer B: {preference_counts['B']} ({preference_counts['B']/total*100:.1f}%)")
    print(f"⚖️  Equal: {preference_counts['equal']} ({preference_counts['equal']/total*100:.1f}%)")
    print(f"📈 Average Confidence: {avg_confidence:.2f}")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
