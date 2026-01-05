"""
Tutorial Case Initializer Tool

This tool finds the most relevant tutorial case based on user requirements
and initializes the target case path with files from the selected tutorial.
"""

import os
import shutil
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from langchain.schema import HumanMessage, SystemMessage
from principia_ai.metrics.tracker import MetricsTracker


class TutorialInitializer:
    """
    Tool for initializing case directories based on tutorial cases.
    
    This tool:
    1. Scans tutorial directories to find complete OpenFOAM cases
    2. Uses LLM to find the most relevant tutorial based on user requirements
    3. Copies the selected tutorial files to initialize the target case
    """
    
    def __init__(self, llm=None):
        self.llm = llm
        self.tutorial_cases_cache = {}
    
    def find_complete_cases(self, tutorial_path: str) -> List[Dict[str, Any]]:
        """
        遍历教程路径，找到所有完整的OpenFOAM案例。
        完整案例的条件：包含 Allrun 和 Allclean 文件。
        
        Args:
            tutorial_path: 教程根目录路径
            
        Returns:
            List of dictionaries containing case information:
            - path: absolute path to the case
            - relative_path: relative path from tutorial_path
            - readme_content: content of README file if exists
            - description: extracted description from case structure
        """
        if not os.path.exists(tutorial_path):
            print(f"Tutorial path does not exist: {tutorial_path}")
            return []
        
        complete_cases = []
        
        def scan_directory(current_path: str, relative_path: str = ""):
            """递归扫描目录寻找完整案例"""
            try:
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)
                    item_relative = os.path.join(relative_path, item) if relative_path else item
                    
                    if os.path.isdir(item_path):
                        # 检查是否为完整案例
                        allrun_path = os.path.join(item_path, "Allrun")
                        allclean_path = os.path.join(item_path, "Allclean")
                        
                        if os.path.exists(allrun_path) and os.path.exists(allclean_path):
                            # 这是一个完整的案例
                            case_info = {
                                "path": item_path,
                                "relative_path": item_relative,
                                "readme_content": self._read_readme(item_path),
                                "description": self._extract_case_description(item_path)
                            }
                            complete_cases.append(case_info)
                            print(f"Found complete case: {item_relative}")
                        else:
                            # 继续递归搜索子目录
                            scan_directory(item_path, item_relative)
            except PermissionError:
                print(f"Permission denied accessing: {current_path}")
            except Exception as e:
                print(f"Error scanning {current_path}: {e}")
        
        print(f"Scanning tutorial directory: {tutorial_path}")
        scan_directory(tutorial_path)
        
        print(f"Found {len(complete_cases)} complete cases")
        return complete_cases
    
    def _read_readme(self, case_path: str) -> Optional[str]:
        """读取案例目录中的README文件"""
        readme_files = ["README", "README.txt", "README.md", "readme", "Readme.txt"]
        
        for readme_file in readme_files:
            readme_path = os.path.join(case_path, readme_file)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    print(f"Error reading {readme_path}: {e}")
        return None
    
    def _extract_case_description(self, case_path: str) -> str:
        """从案例结构中提取描述信息"""
        description_parts = []
        
        # 从路径名推断
        case_name = os.path.basename(case_path)
        description_parts.append(f"Case: {case_name}")
        
        # 检查求解器类型
        control_dict_path = os.path.join(case_path, "system", "controlDict")
        if os.path.exists(control_dict_path):
            try:
                with open(control_dict_path, 'r') as f:
                    content = f.read()
                    # 简单的求解器提取
                    if "application" in content:
                        lines = content.split('\n')
                        for line in lines:
                            if line.strip().startswith("application"):
                                solver = line.split()[-1].rstrip(';')
                                description_parts.append(f"Solver: {solver}")
                                break
            except Exception:
                pass
        
        # 检查物理模型
        physics_info = []
        constant_path = os.path.join(case_path, "constant")
        
        # 检查湍流模型
        turbulence_props = os.path.join(constant_path, "turbulenceProperties")
        if os.path.exists(turbulence_props):
            physics_info.append("turbulence")
        
        # 检查传输属性
        transport_props = os.path.join(constant_path, "transportProperties")
        if os.path.exists(transport_props):
            physics_info.append("transport")
        
        # 检查热物理属性
        thermophys_props = os.path.join(constant_path, "thermophysicalProperties")
        if os.path.exists(thermophys_props):
            physics_info.append("thermophysics")
        
        # 检查相属性
        phase_props = os.path.join(constant_path, "phaseProperties")
        if os.path.exists(phase_props):
            physics_info.append("multiphase")
        
        if physics_info:
            description_parts.append(f"Physics: {', '.join(physics_info)}")
        
        # 检查初始场文件
        zero_path = os.path.join(case_path, "0")
        if os.path.exists(zero_path):
            fields = []
            for item in os.listdir(zero_path):
                if os.path.isfile(os.path.join(zero_path, item)):
                    fields.append(item)
            if fields:
                description_parts.append(f"Fields: {', '.join(sorted(fields))}")
        
        return " | ".join(description_parts)
    
    def find_relevant_tutorial_cases(self, user_request: str, tutorial_cases: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        从知识库的教程案例中找到最相关的案例，使用TutorialInitializer的LLM方法。
        
        Args:
            user_request: 用户需求描述
            tutorial_cases: 从knowledge manager获取的教程案例列表
            top_k: 返回的相关案例数量
            
        Returns:
            List of the most relevant case information dictionaries
        """
        if not tutorial_cases:
            return []
            
        if not self.llm:
            print("Warning: No LLM available. Cannot find relevant tutorial cases.")
            return []
        
        # Use the find_multiple_relevant_cases method
        relevant_cases = self.find_multiple_relevant_cases(user_request, tutorial_cases, top_k)
        
        return relevant_cases
            
    def find_multiple_relevant_cases(self, user_request: str, tutorial_cases: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        使用LLM找到多个最相关的教程案例
        
        Args:
            user_request: 用户需求描述
            tutorial_cases: 可用的教程案例列表
            top_k: 返回的相关案例数量
            
        Returns:
            List of the most relevant case information dictionaries
        """
        if not tutorial_cases:
            print("No tutorial cases available for comparison")
            return []
        
        if not self.llm:
            print("No LLM available, returning first few cases")
            return tutorial_cases[:min(top_k, len(tutorial_cases))]
        
        # 准备案例信息用于LLM分析
        cases_info = []
        for i, case in enumerate(tutorial_cases):
            case_summary = {
                "index": i,
                "path": case["relative_path"],
                "description": case["description"],
                "readme": case["readme_content"][:500] if case["readme_content"] else "No README available"
            }
            cases_info.append(case_summary)
        
        # 构建提示词
        system_prompt = f"""You are an OpenFOAM expert helping to select the {top_k} most relevant tutorial cases for a user's simulation requirements.

Analyze the user request and compare it with the available tutorial cases. Consider:
- Physics phenomena (flow type, turbulence, heat transfer, multiphase, etc.)
- Solver type requirements
- Geometry complexity
- Boundary condition types
- Material properties

Return the indices (0-based) of the {top_k} most relevant cases in order of relevance.

Response format: Only return a JSON array of integers, e.g. [3, 7, 1]"""

        user_prompt = f"""User Request: {user_request}

Available Tutorial Cases:
{json.dumps(cases_info, indent=2)}

Which {top_k} case indices are most relevant for this user request? Return as a JSON array."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Track tokens
            tracker = MetricsTracker()
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
            agent_name = tracker.current_agent or "TutorialInitializer"
            tracker.record_llm_call(
                agent_name=agent_name,
                input_tokens=usage.get('input_tokens', 0),
                output_tokens=usage.get('output_tokens', 0),
                model=self.llm.model_name if hasattr(self.llm, 'model_name') else 'unknown'
            )
            
            # 解析响应获取索引列表
            try:
                import re
                # Try to extract JSON array from response
                json_match = re.search(r'\[.*\]', response.content)
                if json_match:
                    indices_str = json_match.group(0)
                    indices = json.loads(indices_str)
                else:
                    # If not wrapped in proper JSON format, try to parse list-like string
                    indices_str = response.content.strip()
                    indices_str = indices_str.replace('[', '').replace(']', '').replace(' ', '')
                    indices = [int(idx) for idx in indices_str.split(',') if idx]
                
                # Filter valid indices
                valid_indices = [idx for idx in indices if 0 <= idx < len(tutorial_cases)]
                
                # Ensure we don't exceed the requested number of cases
                valid_indices = valid_indices[:top_k]
                
                if not valid_indices:
                    print("No valid indices returned, using first few cases")
                    return tutorial_cases[:min(top_k, len(tutorial_cases))]
                
                # Get the selected cases
                selected_cases = [tutorial_cases[idx] for idx in valid_indices]
                print(f"LLM selected {len(selected_cases)} cases")
                for idx, case in zip(valid_indices, selected_cases):
                    print(f"  Case index {idx}: {case['relative_path']}")
                
                return selected_cases
                
            except Exception as e:
                print(f"Could not parse LLM response as list of indices: {e}. Response: {response.content}")
                # Fall back to first few cases
                return tutorial_cases[:min(top_k, len(tutorial_cases))]
                
        except Exception as e:
            print(f"Error in LLM case selection: {e}")
            return tutorial_cases[:min(top_k, len(tutorial_cases))]
    
    def copy_case_files(self, source_case_path: str, target_case_path: str) -> bool:
        """
        将选定的教程案例文件复制到目标案例路径
        
        Args:
            source_case_path: 源教程案例路径
            target_case_path: 目标案例路径
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # 确保目标目录存在
            os.makedirs(target_case_path, exist_ok=True)
            
            # 复制源案例目录下的所有文件和文件夹
            copied_items = []
            
            for item in os.listdir(source_case_path):
                source_item = os.path.join(source_case_path, item)
                target_item = os.path.join(target_case_path, item)
                
                if os.path.isdir(source_item):
                    # 复制目录
                    if os.path.exists(target_item):
                        shutil.rmtree(target_item)
                    shutil.copytree(source_item, target_item)
                    copied_items.append(f"directory: {item}")
                    print(f"Copied directory: {item}")
                elif os.path.isfile(source_item):
                    # 复制文件
                    shutil.copy2(source_item, target_item)
                    copied_items.append(f"file: {item}")
                    print(f"Copied file: {item}")
            
            print(f"Successfully initialized case from tutorial: {source_case_path}")
            print(f"Copied items: {copied_items}")
            return True
            
        except Exception as e:
            print(f"Error copying case files: {e}")
            return False
    
    def initialize_case_from_tutorial_with_selected_case(self, selected_case: Dict[str, Any], target_case_path: str) -> Dict[str, Any]:
        """
        使用已选择的教程案例初始化目标案例目录
        
        Args:
            selected_case: 已选择的教程案例信息（来自find_relevant_tutorial_cases）
            target_case_path: 目标案例路径
            
        Returns:
            Dictionary with initialization results:
            - success: bool
            - selected_case: dict or None
            - message: str
        """
        print(f"Initializing case from selected tutorial...")
        print(f"Selected case: {selected_case.get('path', 'Unknown')}")
        print(f"Target case path: {target_case_path}")
        
        # Get the tutorial case path from the selected case
        case_path = selected_case.get('path', '')
        if not case_path:
            return {
                "success": False,
                "selected_case": selected_case,
                "message": "Selected case does not have a valid case_path"
            }
        
        # Build the full tutorial path
        BLASTFOAM_TUTORIALS = os.getenv("BLASTFOAM_TUTORIALS")
        if not BLASTFOAM_TUTORIALS:
            return {
                "success": False,
                "selected_case": selected_case,
                "message": "BLASTFOAM_TUTORIALS environment variable not set"
            }
        
        tutorial_path = os.path.join(BLASTFOAM_TUTORIALS, case_path)
        
        if not os.path.exists(tutorial_path):
            return {
                "success": False,
                "selected_case": selected_case,
                "message": f"Tutorial case path does not exist: {tutorial_path}"
            }
        
        # Copy the tutorial case files to target path
        success = self.copy_case_files(tutorial_path, target_case_path)
        
        return {
            "success": success,
            "selected_case": selected_case,
            "message": f"Successfully initialized from {case_path}" if success 
                      else f"Failed to copy files from {case_path}"
        }


def register_tutorial_tools(graph=None) -> Dict[str, Any]:
    """
    Register tutorial initialization tools for use with the tool registry.
    
    Args:
        graph: Optional StateGraph instance (not used but maintained for consistency)
        
    Returns:
        Dictionary of tutorial tools
    """
    # This will be populated when the tool is actually used with an LLM instance
    return {
        "initialize_case_from_tutorial": None  # Placeholder - will be set by agent
    }
