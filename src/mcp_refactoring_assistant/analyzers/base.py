#!/usr/bin/env python3
"""
Base analyzer class for refactoring analysis
"""

import ast
from abc import ABC, abstractmethod
from typing import List

from ..models import RefactoringGuidance


class BaseAnalyzer(ABC):
    """Base class for all code analyzers"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """
        Analyze code and return refactoring guidance
        
        Args:
            content: Python code content
            file_path: Path to the file being analyzed
            tree: Optional pre-parsed AST tree
            
        Returns:
            List of refactoring guidance items
        """
        pass

    def _safe_analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """
        Safely run analysis with error handling
        """
        try:
            return self.analyze(content, file_path, tree)
        except Exception as e:
            print(f"Warning: {self.name} analysis failed: {e}")
            return []