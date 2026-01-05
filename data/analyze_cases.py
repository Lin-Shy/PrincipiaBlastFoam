import os
import re
from collections import Counter

cases_dir = '/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/data/cases_description'
files = [f for f in os.listdir(cases_dir) if f.endswith('.md')]

stats = {
    'total_cases': 0,
    'solvers': Counter(),
    'dimensions': Counter(),
    'features': {
        'reaction_detonation': 0,
        'fsi': 0,
        'amr': 0
    },
    'case_types': Counter()
}

for f in files:
    stats['total_cases'] += 1
    path = os.path.join(cases_dir, f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
        content_lower = content.lower()
        
        # Solver
        solver_match = re.search(r'(?:\*\*Solver:\*\*|openfoam-solver:)\s*"?([^"\n]+)"?', content, re.IGNORECASE)
        if solver_match:
            solver = solver_match.group(1).strip()
            # Clean up solver name
            if 'blastfoam' in solver.lower() and '+' in solver:
                solver = 'blastFoam (coupled)'
            elif 'utility' in solver.lower():
                solver = 'Utility'
            else:
                solver = solver.split(',')[0].strip()
            stats['solvers'][solver] += 1
        else:
            # Fallback for some files that might not have the standard header
            if 'icoFoam' in content:
                stats['solvers']['icoFoam'] += 1
            else:
                stats['solvers']['Unknown'] += 1

        # Case Type
        type_match = re.search(r'case-type:\s*"?([^"\n]+)"?', content, re.IGNORECASE)
        if type_match:
            ctype = type_match.group(1).strip().lower()
            stats['case_types'][ctype] += 1
        else:
            if "validation" in content_lower:
                stats['case_types']['validation'] += 1
            elif "utility" in content_lower:
                stats['case_types']['utility'] += 1
            else:
                stats['case_types']['tutorial'] += 1

        # Dimensions (Priority: 3D > Axisymmetric > 2D > 1D)
        if '3d' in content_lower:
            stats['dimensions']['3D'] += 1
        elif 'axisymmetric' in content_lower or 'wedge' in content_lower:
            stats['dimensions']['2D Axisymmetric'] += 1
        elif '2d' in content_lower:
            stats['dimensions']['2D'] += 1
        elif '1d' in content_lower:
            stats['dimensions']['1D'] += 1
        else:
            stats['dimensions']['Unknown'] += 1

        # Features
        if any(x in content_lower for x in ['reacting', 'combustion', 'detonation', 'chemical reaction', 'ignition']):
            stats['features']['reaction_detonation'] += 1
        
        if any(x in content_lower for x in ['fsi', 'fluid-structure', 'coupled', 'deformation', 'solid mechanics']):
            stats['features']['fsi'] += 1
            
        if any(x in content_lower for x in ['adaptive', 'amr', 'dynamicmesh', 'refinement']):
            stats['features']['amr'] += 1

print(stats)
