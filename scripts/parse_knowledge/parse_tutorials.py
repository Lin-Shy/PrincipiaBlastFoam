"""
Parser for extracting OpenFOAM knowledge fragments from tutorial cases.

This script analyzes OpenFOAM tutorial cases and extracts structured knowledge 
fragments to populate the knowledge graph.
"""

import os
import re
import json
import uuid
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

# Import our schema definitions
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OpenFOAMParser:
    """Parser for OpenFOAM dictionary files to extract knowledge fragments."""
    
    def __init__(self, output_dir: str):
        """
        Initialize the parser.
        
        Args:
            output_dir: Directory to save extracted knowledge fragments
        """
        self.output_dir = output_dir
        self.fragments = {}
        self.tutorial_cases = {}
        self.solvers = {}
        self.physics_models = {}
        self.relationships = []
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def parse_tutorial_cases(self, base_dir: str):
        """
        Parse all tutorial cases from the given directory.
        
        Args:
            base_dir: Base directory containing tutorial cases
        """
        for root, dirs, files in os.walk(base_dir):
            # Skip hidden directories and files
            if any(part.startswith('.') for part in root.split(os.sep)):
                continue
                
            # Check if this looks like an OpenFOAM case
            if 'system' in dirs and '0' in dirs and 'constant' in dirs:
                case_path = root
                case_name = os.path.relpath(case_path, base_dir)
                print(f"Processing case: {case_name}")
                
                # Parse the case
                self.parse_case(case_path, case_name)
    
    def parse_case(self, case_path: str, case_name: str):
        """
        Parse a single OpenFOAM tutorial case.
        
        Args:
            case_path: Path to the case directory
            case_name: Name of the case
        """
        # Create tutorial case entity
        case_id = f"TutorialCase_{self.sanitize_id(case_name)}"
        
        # Determine solver from controlDict
        control_dict_path = os.path.join(case_path, "system", "controlDict")
        solver = self.get_solver_from_control_dict(control_dict_path)
        
        # Determine physics model from other files
        physics_model = self.infer_physics_model(case_path)
        
        tutorial_case = {
            "id": case_id,
            "name": case_name,
            "path": case_path,
            "solver": solver,
            "physics_model": physics_model,
            "description": f"OpenFOAM tutorial case: {case_name}",
            "fragments": []
        }
        
        self.tutorial_cases[case_id] = tutorial_case
        
        # Register solver if not already registered
        solver_id = f"Solver_{solver}"
        if solver_id not in self.solvers:
            self.solvers[solver_id] = {
                "id": solver_id,
                "name": solver,
                "description": f"OpenFOAM solver: {solver}"
            }
            
        # Register physics model if not already registered
        model_id = f"PhysicsModel_{physics_model}"
        if model_id not in self.physics_models:
            self.physics_models[model_id] = {
                "id": model_id,
                "name": physics_model,
                "type": physics_model,
                "description": f"Physics model: {physics_model}"
            }
            
        # Create relationships
        self.relationships.append({
            "source_id": case_id,
            "target_id": solver_id,
            "relationship_type": "USES_SOLVER",
            "properties": {}
        })
        
        self.relationships.append({
            "source_id": case_id,
            "target_id": model_id,
            "relationship_type": "HAS_MODEL",
            "properties": {}
        })
        
        # Parse each file in the case
        self.parse_system_directory(case_path, case_id)
        self.parse_constant_directory(case_path, case_id)
        self.parse_time_directories(case_path, case_id)
    
    def parse_system_directory(self, case_path: str, case_id: str):
        """
        Parse files in the system directory.
        
        Args:
            case_path: Path to the case directory
            case_id: ID of the tutorial case
        """
        system_dir = os.path.join(case_path, "system")
        
        # Parse controlDict
        control_dict_path = os.path.join(system_dir, "controlDict")
        if os.path.exists(control_dict_path):
            self.parse_control_dict(control_dict_path, case_id)
        
        # Parse fvSolution
        fv_solution_path = os.path.join(system_dir, "fvSolution")
        if os.path.exists(fv_solution_path):
            self.parse_fv_solution(fv_solution_path, case_id)
        
        # Parse fvSchemes
        fv_schemes_path = os.path.join(system_dir, "fvSchemes")
        if os.path.exists(fv_schemes_path):
            self.parse_fv_schemes(fv_schemes_path, case_id)
        
        # Parse blockMeshDict
        block_mesh_path = os.path.join(system_dir, "blockMeshDict")
        if os.path.exists(block_mesh_path):
            self.parse_block_mesh_dict(block_mesh_path, case_id)
    
    def parse_constant_directory(self, case_path: str, case_id: str):
        """
        Parse files in the constant directory.
        
        Args:
            case_path: Path to the case directory
            case_id: ID of the tutorial case
        """
        constant_dir = os.path.join(case_path, "constant")
        
        # Parse transportProperties
        transport_props_path = os.path.join(constant_dir, "transportProperties")
        if os.path.exists(transport_props_path):
            self.parse_transport_properties(transport_props_path, case_id)
        
        # Parse turbulenceProperties
        turbulence_props_path = os.path.join(constant_dir, "turbulenceProperties")
        if os.path.exists(turbulence_props_path):
            self.parse_turbulence_properties(turbulence_props_path, case_id)
    
    def parse_time_directories(self, case_path: str, case_id: str):
        """
        Parse files in time directories (0, 0.orig, etc).
        
        Args:
            case_path: Path to the case directory
            case_id: ID of the tutorial case
        """
        # Look for time directories (0, 0.orig)
        for time_dir in ["0", "0.orig"]:
            time_path = os.path.join(case_path, time_dir)
            if os.path.exists(time_path) and os.path.isdir(time_path):
                # Process each field file (U, p, k, etc)
                for filename in os.listdir(time_path):
                    file_path = os.path.join(time_path, filename)
                    if os.path.isfile(file_path):
                        # Skip hidden files
                        if filename.startswith('.'):
                            continue
                        self.parse_field_file(file_path, case_id, time_dir, filename)
    
    def parse_control_dict(self, file_path: str, case_id: str):
        """
        Parse controlDict file to extract knowledge fragments.
        
        Args:
            file_path: Path to the controlDict file
            case_id: ID of the tutorial case
        """
        # Extract time controls
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Extract time control settings
            time_controls = self.extract_section(content, None)
            if time_controls:
                fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                fragment = {
                    "id": fragment_id,
                    "fragment_type": "TimeControls",
                    "target_file": "system/controlDict",
                    "entity_key": None,
                    "content": time_controls,
                    "description": "Time control settings for simulation"
                }
                
                self.fragments[fragment_id] = fragment
                self.tutorial_cases[case_id]["fragments"].append(fragment_id)
                
                # Create relationship
                self.relationships.append({
                    "source_id": fragment_id,
                    "target_id": case_id,
                    "relationship_type": "BELONGS_TO_CASE",
                    "properties": {}
                })
                
        except Exception as e:
            print(f"Error parsing controlDict {file_path}: {e}")
    
    def parse_fv_solution(self, file_path: str, case_id: str):
        """
        Parse fvSolution file to extract solver settings.
        
        Args:
            file_path: Path to the fvSolution file
            case_id: ID of the tutorial case
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract solvers section
            solvers_section = self.extract_section(content, "solvers")
            if not solvers_section:
                return
                
            # Extract individual solver settings
            solver_pattern = r'(\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
            for match in re.finditer(solver_pattern, solvers_section):
                field = match.group(1)
                solver_settings = match.group(0)
                
                fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                fragment = {
                    "id": fragment_id,
                    "fragment_type": "SolverSetting",
                    "target_file": "system/fvSolution",
                    "entity_key": field,
                    "content": solver_settings,
                    "description": f"Solver settings for field {field}"
                }
                
                self.fragments[fragment_id] = fragment
                self.tutorial_cases[case_id]["fragments"].append(fragment_id)
                
                # Create relationship
                self.relationships.append({
                    "source_id": fragment_id,
                    "target_id": case_id,
                    "relationship_type": "BELONGS_TO_CASE",
                    "properties": {}
                })
                
            # Extract other sections like SIMPLE, PIMPLE, relaxationFactors
            for section_name in ["SIMPLE", "PIMPLE", "relaxationFactors"]:
                section = self.extract_section(content, section_name)
                if section:
                    fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                    fragment = {
                        "id": fragment_id,
                        "fragment_type": f"Algorithm_{section_name}",
                        "target_file": "system/fvSolution",
                        "entity_key": None,
                        "content": section,
                        "description": f"{section_name} algorithm settings"
                    }
                    
                    self.fragments[fragment_id] = fragment
                    self.tutorial_cases[case_id]["fragments"].append(fragment_id)
                    
                    # Create relationship
                    self.relationships.append({
                        "source_id": fragment_id,
                        "target_id": case_id,
                        "relationship_type": "BELONGS_TO_CASE",
                        "properties": {}
                    })
                    
        except Exception as e:
            print(f"Error parsing fvSolution {file_path}: {e}")
    
    def parse_fv_schemes(self, file_path: str, case_id: str):
        """
        Parse fvSchemes file to extract discretization schemes.
        
        Args:
            file_path: Path to the fvSchemes file
            case_id: ID of the tutorial case
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract each scheme section
            scheme_sections = [
                "ddtSchemes", "gradSchemes", "divSchemes", 
                "laplacianSchemes", "interpolationSchemes", "snGradSchemes"
            ]
            
            for section_name in scheme_sections:
                section = self.extract_section(content, section_name)
                if section:
                    fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                    fragment = {
                        "id": fragment_id,
                        "fragment_type": "DiscretizationScheme",
                        "target_file": "system/fvSchemes",
                        "entity_key": section_name,
                        "content": section,
                        "description": f"{section_name} discretization settings"
                    }
                    
                    self.fragments[fragment_id] = fragment
                    self.tutorial_cases[case_id]["fragments"].append(fragment_id)
                    
                    # Create relationship
                    self.relationships.append({
                        "source_id": fragment_id,
                        "target_id": case_id,
                        "relationship_type": "BELONGS_TO_CASE",
                        "properties": {}
                    })
                    
        except Exception as e:
            print(f"Error parsing fvSchemes {file_path}: {e}")
    
    def parse_block_mesh_dict(self, file_path: str, case_id: str):
        """
        Parse blockMeshDict file to extract mesh sections.
        
        Args:
            file_path: Path to the blockMeshDict file
            case_id: ID of the tutorial case
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Get case name for geometry identification
            case_name = self.tutorial_cases[case_id]["name"].split('/')[-1]
            
            # Extract the entire blockMeshDict as one fragment
            fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
            fragment = {
                "id": fragment_id,
                "fragment_type": "MeshDict",
                "target_file": "system/blockMeshDict",
                "entity_key": case_name,  # Use case name as entity key for geometry identification
                "content": content,
                "description": f"Block mesh definition for {case_name} geometry"
            }
            
            self.fragments[fragment_id] = fragment
            self.tutorial_cases[case_id]["fragments"].append(fragment_id)
            
            # Create relationship
            self.relationships.append({
                "source_id": fragment_id,
                "target_id": case_id,
                "relationship_type": "BELONGS_TO_CASE",
                "properties": {}
            })
            
            # Also extract individual sections for more granular reuse
            for section_name in ["vertices", "blocks", "edges", "boundary"]:
                section = self.extract_section(content, section_name)
                if section:
                    sub_fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                    sub_fragment = {
                        "id": sub_fragment_id,
                        "fragment_type": f"MeshDict_{section_name}",
                        "target_file": "system/blockMeshDict",
                        "entity_key": case_name,
                        "content": section,
                        "description": f"{section_name} section for {case_name} mesh"
                    }
                    
                    self.fragments[sub_fragment_id] = sub_fragment
                    self.tutorial_cases[case_id]["fragments"].append(sub_fragment_id)
                    
                    # Create relationship
                    self.relationships.append({
                        "source_id": sub_fragment_id,
                        "target_id": case_id,
                        "relationship_type": "BELONGS_TO_CASE",
                        "properties": {}
                    })
                    
        except Exception as e:
            print(f"Error parsing blockMeshDict {file_path}: {e}")
    
    def parse_transport_properties(self, file_path: str, case_id: str):
        """
        Parse transportProperties file to extract physical properties.
        
        Args:
            file_path: Path to the transportProperties file
            case_id: ID of the tutorial case
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract the entire transportProperties as one fragment
            fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
            fragment = {
                "id": fragment_id,
                "fragment_type": "TransportProperties",
                "target_file": "constant/transportProperties",
                "entity_key": None,
                "content": content,
                "description": "Transport properties for the simulation"
            }
            
            self.fragments[fragment_id] = fragment
            self.tutorial_cases[case_id]["fragments"].append(fragment_id)
            
            # Create relationship
            self.relationships.append({
                "source_id": fragment_id,
                "target_id": case_id,
                "relationship_type": "BELONGS_TO_CASE",
                "properties": {}
            })
            
        except Exception as e:
            print(f"Error parsing transportProperties {file_path}: {e}")
    
    def parse_turbulence_properties(self, file_path: str, case_id: str):
        """
        Parse turbulenceProperties file to extract turbulence model settings.
        
        Args:
            file_path: Path to the turbulenceProperties file
            case_id: ID of the tutorial case
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract the entire turbulenceProperties as one fragment
            fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
            fragment = {
                "id": fragment_id,
                "fragment_type": "TurbulenceModelProperties",
                "target_file": "constant/turbulenceProperties",
                "entity_key": None,
                "content": content,
                "description": "Turbulence model configuration"
            }
            
            self.fragments[fragment_id] = fragment
            self.tutorial_cases[case_id]["fragments"].append(fragment_id)
            
            # Create relationship
            self.relationships.append({
                "source_id": fragment_id,
                "target_id": case_id,
                "relationship_type": "BELONGS_TO_CASE",
                "properties": {}
            })
            
            # Try to identify the specific turbulence model
            model_match = re.search(r'simulationType\s+(\w+)', content)
            if model_match:
                sim_type = model_match.group(1)
                if sim_type == "RAS":
                    ras_model = re.search(r'RASModel\s+(\w+)', content)
                    if ras_model:
                        # Update the physics model if we found a specific turbulence model
                        model_name = ras_model.group(1)
                        self.tutorial_cases[case_id]["physics_model"] = model_name
                        
                        # Create or update the physics model entity
                        model_id = f"PhysicsModel_{model_name}"
                        if model_id not in self.physics_models:
                            self.physics_models[model_id] = {
                                "id": model_id,
                                "name": model_name,
                                "type": "Turbulence",
                                "description": f"Turbulence model: {model_name}"
                            }
                            
                        # Update relationship
                        for rel in self.relationships:
                            if (rel["source_id"] == case_id and 
                                rel["relationship_type"] == "HAS_MODEL"):
                                rel["target_id"] = model_id
                                break
                
        except Exception as e:
            print(f"Error parsing turbulenceProperties {file_path}: {e}")
    
    def parse_field_file(self, file_path: str, case_id: str, time_dir: str, field_name: str):
        """
        Parse a field file to extract boundary conditions.
        
        Args:
            file_path: Path to the field file
            case_id: ID of the tutorial case
            time_dir: Time directory name (0, 0.orig)
            field_name: Field name (U, p, etc.)
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract dimensions
            dimensions_match = re.search(r'dimensions\s+\[(.*?)\]', content)
            dimensions = dimensions_match.group(1) if dimensions_match else ""
            
            # Extract internal field
            internal_field_match = re.search(r'internalField\s+(\w+)\s*(.*?);', content, re.DOTALL)
            if internal_field_match:
                internal_field_type = internal_field_match.group(1)  # uniform, nonuniform
                internal_field_value = internal_field_match.group(2)  # the actual value
                
                # Create a fragment for the internal field
                fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                fragment = {
                    "id": fragment_id,
                    "fragment_type": "InternalField",
                    "target_file": f"{time_dir}/{field_name}",
                    "entity_key": field_name,
                    "content": f"dimensions [{dimensions}];\n\ninternalField {internal_field_type} {internal_field_value};",
                    "description": f"Initial {field_name} field definition"
                }
                
                self.fragments[fragment_id] = fragment
                self.tutorial_cases[case_id]["fragments"].append(fragment_id)
                
                # Create relationship
                self.relationships.append({
                    "source_id": fragment_id,
                    "target_id": case_id,
                    "relationship_type": "BELONGS_TO_CASE",
                    "properties": {}
                })
            
            # Extract boundaryField section
            boundary_field = self.extract_section(content, "boundaryField")
            if not boundary_field:
                return
                
            # Extract individual boundary conditions
            boundary_pattern = r'(\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
            for match in re.finditer(boundary_pattern, boundary_field):
                boundary_name = match.group(1)
                boundary_settings = match.group(0)
                
                fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"
                fragment = {
                    "id": fragment_id,
                    "fragment_type": "BoundaryCondition",
                    "target_file": f"{time_dir}/{field_name}",
                    "entity_key": f"{field_name}_{boundary_name}",
                    "content": boundary_settings,
                    "description": f"{boundary_name} boundary condition for {field_name}"
                }
                
                self.fragments[fragment_id] = fragment
                self.tutorial_cases[case_id]["fragments"].append(fragment_id)
                
                # Create relationship
                self.relationships.append({
                    "source_id": fragment_id,
                    "target_id": case_id,
                    "relationship_type": "BELONGS_TO_CASE",
                    "properties": {}
                })
                
        except Exception as e:
            print(f"Error parsing field file {file_path}: {e}")
    
    def get_solver_from_control_dict(self, control_dict_path: str) -> str:
        """
        Extract solver name from controlDict.
        
        Args:
            control_dict_path: Path to the controlDict file
            
        Returns:
            Name of the solver
        """
        default_solver = "unknown"
        
        if not os.path.exists(control_dict_path):
            return default_solver
            
        try:
            with open(control_dict_path, 'r') as f:
                content = f.read()
                
            # Look for application entry
            app_match = re.search(r'application\s+(\w+)', content)
            if app_match:
                return app_match.group(1)
                
        except Exception:
            pass
            
        return default_solver
    
    def infer_physics_model(self, case_path: str) -> str:
        """
        Infer the physics model from case files.
        
        Args:
            case_path: Path to the case directory
            
        Returns:
            Name of the physics model
        """
        # Check for turbulence properties first
        turbulence_props_path = os.path.join(case_path, "constant", "turbulenceProperties")
        if os.path.exists(turbulence_props_path):
            try:
                with open(turbulence_props_path, 'r') as f:
                    content = f.read()
                    
                # Look for simulationType entry
                sim_type_match = re.search(r'simulationType\s+(\w+)', content)
                if sim_type_match:
                    sim_type = sim_type_match.group(1)
                    
                    # If it's RAS, try to get the specific model
                    if sim_type == "RAS":
                        ras_model = re.search(r'RASModel\s+(\w+)', content)
                        if ras_model:
                            return ras_model.group(1)
                        return "RAS"
                    elif sim_type == "LES":
                        les_model = re.search(r'LESModel\s+(\w+)', content)
                        if les_model:
                            return les_model.group(1)
                        return "LES"
                    return sim_type
            except Exception:
                pass
        
        # If no turbulence model, check if it's multiphase
        phase_props_path = os.path.join(case_path, "constant", "phaseProperties")
        if os.path.exists(phase_props_path):
            return "Multiphase"
        
        # Default to Laminar if nothing else found
        return "Laminar"
    
    def extract_section(self, content: str, section_name: Optional[str]) -> Optional[str]:
        """
        Extract a dictionary section from OpenFOAM content.
        
        Args:
            content: File content
            section_name: Name of the section to extract, or None for the entire content
            
        Returns:
            Extracted section content, or None if not found
        """
        if section_name is None:
            return content
            
        pattern = rf'{section_name}\s*\n*\s*\{{([^{{}}]*(?:\{{[^{{}}]*\}}[^{{}}]*)*)\}}'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            return f"{section_name}\n{{\n{match.group(1)}\n}}"
        return None
    
    def sanitize_id(self, name: str) -> str:
        """
        Sanitize a name to be used as an ID.
        
        Args:
            name: Name to sanitize
            
        Returns:
            Sanitized name
        """
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    def save_to_json(self):
        """Save extracted knowledge to JSON files."""
        fragments_path = os.path.join(self.output_dir, "fragments.json")
        cases_path = os.path.join(self.output_dir, "tutorial_cases.json")
        solvers_path = os.path.join(self.output_dir, "solvers.json")
        models_path = os.path.join(self.output_dir, "physics_models.json")
        relationships_path = os.path.join(self.output_dir, "relationships.json")
        
        with open(fragments_path, 'w') as f:
            json.dump(self.fragments, f, indent=2)
            
        with open(cases_path, 'w') as f:
            json.dump(self.tutorial_cases, f, indent=2)
            
        with open(solvers_path, 'w') as f:
            json.dump(self.solvers, f, indent=2)
            
        with open(models_path, 'w') as f:
            json.dump(self.physics_models, f, indent=2)
            
        with open(relationships_path, 'w') as f:
            json.dump(self.relationships, f, indent=2)
            
        print(f"Saved {len(self.fragments)} fragments, {len(self.tutorial_cases)} cases, "
              f"{len(self.solvers)} solvers, {len(self.physics_models)} models, "
              f"and {len(self.relationships)} relationships to {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Extract OpenFOAM knowledge fragments from tutorial cases")
    parser.add_argument("--tutorials-dir", required=True, help="Path to OpenFOAM tutorials directory")
    parser.add_argument("--output-dir", required=True, help="Path to save extracted knowledge fragments")
    
    args = parser.parse_args()
    
    parser = OpenFOAMParser(args.output_dir)
    parser.parse_tutorial_cases(args.tutorials_dir)
    parser.save_to_json()


if __name__ == "__main__":
    main()
