import os
from typing import List, Dict, Any
from langchain_core.tools import tool

@tool
def edit_files(path: str, edits: List[Dict[str, Any]]):
    """Edit files by replacing text.
    
    Args:
        path: The path to the file to edit.
        edits: A list of dictionaries, each containing 'old_text' and 'new_text'.
               Example: [{'old_text': 'foo', 'new_text': 'bar'}]
    """
    try:
        if not os.path.exists(path):
            return f"Error: File {path} does not exist."
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for edit in edits:
            old_text = edit.get('old_text')
            new_text = edit.get('new_text')
            if old_text and new_text is not None:
                if old_text not in content:
                    return f"Error: Could not find text '{old_text}' in {path}"
                content = content.replace(old_text, new_text)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"Successfully edited file: {path}"
    except Exception as e:
        return f"Error editing file {path}: {str(e)}"