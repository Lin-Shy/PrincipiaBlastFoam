from typing import List
from langchain.tools import StructuredTool

# Import new tools
from principia_ai.tools.edit.create_directory import create_directory
from principia_ai.tools.edit.create_file import create_file
from principia_ai.tools.edit.edit_files import edit_files
from principia_ai.tools.execute.run_in_terminal import run_in_terminal
from principia_ai.tools.read.read_file import read_file
from principia_ai.tools.search.file_search import file_search
from principia_ai.tools.search.find_usages import find_usages
from principia_ai.tools.search.get_changes import get_changes
from principia_ai.tools.search.list_directory import list_directory
from principia_ai.tools.search.search_codebase import search_codebase
from principia_ai.tools.search.text_search import text_search

def get_edit_tools() -> List[StructuredTool]:
    """
    Returns a list of tools for editing files and directories.
    """
    return [
        create_directory,
        create_file,
        edit_files
    ]

def get_execute_tools() -> List[StructuredTool]:
    """
    Returns a list of tools for executing commands.
    """
    return [
        run_in_terminal
    ]

def get_read_tools() -> List[StructuredTool]:
    """
    Returns a list of tools for reading files.
    """
    return [
        read_file
    ]

def get_search_tools() -> List[StructuredTool]:
    """
    Returns a list of tools for searching the codebase.
    """
    return [
        file_search,
        find_usages,
        get_changes,
        list_directory,
        search_codebase,
        text_search
    ]
