#!/usr/bin/env python3
"""
Shared pytest fixtures and configuration for mcp-python-refactoring tests.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable
from unittest.mock import Mock, MagicMock, patch
import json

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_refactoring_assistant.core import EnhancedRefactoringAnalyzer
from mcp_refactoring_assistant.models import RefactoringGuidance, ExtractableBlock


# ===== BASIC FIXTURES =====

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary Python file for testing."""
    def _create_file(content: str, filename: str = "test.py") -> Path:
        file_path = temp_dir / filename
        file_path.write_text(content)
        return file_path
    return _create_file


@pytest.fixture
def analyzer():
    """Create an EnhancedRefactoringAnalyzer instance for testing."""
    return EnhancedRefactoringAnalyzer()


@pytest.fixture
def analyzer_with_path(temp_dir):
    """Create an analyzer with a specific project path."""
    return EnhancedRefactoringAnalyzer(project_path=str(temp_dir))


# ===== CODE SAMPLE FIXTURES =====

@pytest.fixture
def simple_function_code():
    """Simple, clean function code."""
    return '''
def greet(name):
    """Return a greeting message."""
    return f"Hello, {name}!"

def calculate_area(width, height):
    """Calculate rectangular area."""
    return width * height
'''


@pytest.fixture
def complex_function_code():
    """Complex function with multiple issues."""
    return '''
def complex_calculation(a, b, c, d, e, f, g, h, i, j):
    """Function with too many parameters and high complexity."""
    result = []
    
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                if h > 0:
                                    if i > 0:
                                        if j > 0:
                                            for x in range(100):
                                                if x % 2 == 0:
                                                    if x % 4 == 0:
                                                        result.append(x * 2)
                                                    else:
                                                        result.append(x)
                                                else:
                                                    if x % 3 == 0:
                                                        result.append(x * 3)
                                                    else:
                                                        result.append(x + 1)
    return result
'''


@pytest.fixture
def long_function_code():
    """Long function suitable for extract method refactoring."""
    lines = [
        "def process_data(data):",
        '    """Process data with many steps."""',
        "    # Data validation",
        "    if not data:",
        "        raise ValueError('Data cannot be empty')",
        "",
        "    # Data cleaning",
        "    cleaned_data = []",
        "    for item in data:",
        "        if item is not None:",
        "            cleaned_data.append(str(item).strip())",
        "",
        "    # Data transformation",
        "    transformed_data = []",
        "    for item in cleaned_data:",
        "        if item.isdigit():",
        "            transformed_data.append(int(item))",
        "        else:",
            "            transformed_data.append(item.upper())",
        "",
        "    # Data aggregation",
        "    numbers = [x for x in transformed_data if isinstance(x, int)]",
        "    strings = [x for x in transformed_data if isinstance(x, str)]",
        "",
        "    # Statistical calculations",
        "    if numbers:",
        "        avg = sum(numbers) / len(numbers)",
        "        max_val = max(numbers)",
        "        min_val = min(numbers)",
        "    else:",
        "        avg = max_val = min_val = 0",
        "",
        "    # String processing",
        "    if strings:",
        "        longest_string = max(strings, key=len)",
        "        shortest_string = min(strings, key=len)",
        "        total_length = sum(len(s) for s in strings)",
        "    else:",
        "        longest_string = shortest_string = ''",
        "        total_length = 0",
        "",
        "    # Result compilation",
        "    result = {",
        "        'numbers': numbers,",
        "        'strings': strings,",
        "        'stats': {",
        "            'avg': avg,",
        "            'max': max_val,",
        "            'min': min_val,",
        "            'longest_string': longest_string,",
        "            'shortest_string': shortest_string,",
        "            'total_length': total_length",
        "        }",
        "    }",
        "",
        "    # Final validation",
        "    if not result['numbers'] and not result['strings']:",
        "        raise ValueError('No valid data found')",
        "",
        "    return result"
    ]
    return '\n'.join(lines)


@pytest.fixture
def class_with_methods_code():
    """Class with multiple methods for testing."""
    return '''
class DataProcessor:
    """A class for processing data."""
    
    def __init__(self):
        self.data = []
        self.processed = False
    
    def add_data(self, item):
        """Add an item to the data list."""
        self.data.append(item)
    
    def process(self):
        """Process all data items."""
        if not self.data:
            return []
        
        result = []
        for item in self.data:
            if isinstance(item, (int, float)):
                result.append(item * 2)
            elif isinstance(item, str):
                result.append(item.upper())
            else:
                result.append(str(item))
        
        self.processed = True
        return result
    
    def get_stats(self):
        """Get statistics about the data."""
        if not self.processed:
            self.process()
        
        numbers = [x for x in self.data if isinstance(x, (int, float))]
        if numbers:
            return {
                'count': len(numbers),
                'sum': sum(numbers),
                'avg': sum(numbers) / len(numbers)
            }
        return {'count': 0, 'sum': 0, 'avg': 0}
'''


@pytest.fixture
def syntax_error_code():
    """Code with syntax errors."""
    return '''
def broken_function(
    # Missing closing parenthesis
    return "This will fail"

def another_broken():
    if True
        # Missing colon
        print("broken")
'''


@pytest.fixture
def dead_code_sample():
    """Code with unused functions."""
    return '''
def used_function():
    """This function is called."""
    return "used"

def unused_function():
    """This function is never called."""
    return "unused"

def another_unused():
    """Another unused function."""
    pass

def main():
    """Main function that uses some functions."""
    result = used_function()
    print(result)
    return result

if __name__ == "__main__":
    main()
'''


# ===== CODE FACTORY FIXTURES =====

@pytest.fixture
def code_factory():
    """Factory for generating test code with specific characteristics."""
    
    def _make_function(self, name: str = "test_func", 
                      params: int = 2, 
                      complexity: int = 1, 
                      lines: int = 10) -> str:
        """Generate a function with specified characteristics."""
        param_list = ", ".join([f"param{i}" for i in range(1, params + 1)])
        
        header = f"def {name}({param_list}):"
        docstring = f'    """Generated function with {params} params, complexity {complexity}."""'
        
        body_lines = []
        
        # Add complexity through nested conditions
        indent = "    "
        for i in range(complexity):
            condition = f"{indent}if param1 > {i}:"
            body_lines.append(condition)
            indent += "    "
        
        # Add remaining lines
        remaining_lines = max(1, lines - len(body_lines) - 2)  # -2 for header and docstring
        for i in range(remaining_lines):
            body_lines.append(f"{indent}result_{i} = param1 + {i}")
        
        body_lines.append(f"{indent}return result_0")
        
        return "\n".join([header, docstring] + body_lines)
    
    def _make_class(self, name: str = "TestClass", 
                   methods: int = 3,
                   complexity: int = 1) -> str:
        """Generate a class with specified characteristics."""
        lines = [f"class {name}:", f'    """Generated class with {methods} methods."""', ""]
        
        # Add constructor
        lines.extend([
            "    def __init__(self):",
            "        self.value = 0",
            ""
        ])
        
        # Add methods
        for i in range(methods):
            method_code = _make_function(self, name=f"method_{i}", params=2, complexity=complexity, lines=5)
            # Indent method code
            method_lines = [f"    {line}" if line.strip() else "" for line in method_code.split('\n')]
            lines.extend(method_lines)
            lines.append("")
        
        return "\n".join(lines)
    
    return type('CodeFactory', (), {
        'make_function': _make_function,
        'make_class': _make_class
    })()


# ===== PARAMETER FIXTURES =====

@pytest.fixture(params=[
    ("simple", "def simple(): return True"),
    ("with_params", "def with_params(a, b): return a + b"),
    ("with_docstring", 'def with_docstring():\n    """Test function"""\n    return True'),
    ("empty_body", "def empty_body(): pass")
])
def function_samples(request):
    """Parametrized fixture providing various function samples."""
    name, code = request.param
    return {"name": name, "code": code}


@pytest.fixture(params=[1, 3, 5, 10])
def complexity_levels(request):
    """Different complexity levels for testing."""
    return request.param


@pytest.fixture(params=[10, 25, 50, 100])
def function_lengths(request):
    """Different function lengths for testing."""
    return request.param


# ===== MOCK FIXTURES =====

@pytest.fixture
def mock_analyzer():
    """Mock analyzer for testing without real analysis."""
    mock = Mock(spec=EnhancedRefactoringAnalyzer)
    mock.analyze_file.return_value = []
    mock.project_path = "/mock/path"
    return mock


@pytest.fixture
def mock_guidance():
    """Mock RefactoringGuidance objects."""
    def _create_guidance(issue_type: str = "test_issue",
                        severity: str = "medium",
                        description: str = "Test description") -> RefactoringGuidance:
        return RefactoringGuidance(
            issue_type=issue_type,
            severity=severity,
            location="test.py:1:0",
            description=description,
            benefits=["Test benefit"],
            precise_steps=["Test step 1", "Test step 2"],
            extractable_blocks=[]
        )
    return _create_guidance


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for protocol testing."""
    server_mock = Mock()
    server_mock.list_tools.return_value = [
        {"name": "analyze_python_code"},
        {"name": "extract_function"},
        {"name": "quick_analyze"}
    ]
    return server_mock


# ===== ASSERTION HELPERS =====

@pytest.fixture
def guidance_validator():
    """Helper for validating RefactoringGuidance objects."""
    
    def validate(guidance: List[RefactoringGuidance]) -> None:
        """Validate a list of RefactoringGuidance objects."""
        assert isinstance(guidance, list)
        
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)
            assert hasattr(item, 'issue_type') and item.issue_type
            assert hasattr(item, 'severity') and item.severity in ['low', 'medium', 'high', 'critical']
            assert hasattr(item, 'location') and item.location
            assert hasattr(item, 'description') and item.description
            assert hasattr(item, 'benefits') and isinstance(item.benefits, list)
            assert hasattr(item, 'precise_steps') and isinstance(item.precise_steps, list)
            
            # Validate dict conversion
            item_dict = item.to_dict()
            assert isinstance(item_dict, dict)
            assert 'issue_type' in item_dict
            assert 'severity' in item_dict
    
    return validate


@pytest.fixture
def performance_timer():
    """Helper for timing operations."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            self.end_time = time.time()
        
        @property
        def elapsed(self) -> float:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0.0
    
    return Timer


# ===== FILE SYSTEM FIXTURES =====

@pytest.fixture
def test_project_structure(temp_dir):
    """Create a realistic project structure for testing."""
    # Create directories
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "myproject").mkdir()
    (temp_dir / "tests").mkdir()
    (temp_dir / "docs").mkdir()
    
    # Create Python files
    files_to_create = {
        "src/myproject/__init__.py": "",
        "src/myproject/main.py": '''
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
''',
        "src/myproject/utils.py": '''
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
''',
        "tests/__init__.py": "",
        "tests/test_main.py": '''
def test_main():
    assert True
''',
        "README.md": "# Test Project",
        "requirements.txt": "pytest\nrequests"
    }
    
    for file_path, content in files_to_create.items():
        full_path = temp_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    return temp_dir


# ===== CONFIGURATION FIXTURES =====

@pytest.fixture
def analyzer_config():
    """Configuration options for the analyzer."""
    return {
        "line_threshold": 20,
        "complexity_threshold": 10,
        "parameter_threshold": 5,
        "enable_dead_code_detection": True,
        "enable_extract_method": True
    }


# ===== SNAPSHOT TESTING HELPERS =====

@pytest.fixture
def snapshot_dir(temp_dir):
    """Directory for storing test snapshots."""
    snapshot_path = temp_dir / "snapshots"
    snapshot_path.mkdir()
    return snapshot_path


# ===== PYTEST MARKERS AUTO-ASSIGNMENT =====

def pytest_configure(config):
    """Configure pytest markers automatically."""
    # Auto-assign markers based on test names
    pass


def pytest_collection_modifyitems(config, items):
    """Automatically assign markers based on test patterns."""
    for item in items:
        # Mark tests as unit if they're in unit directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark tests as functional if they're in functional directory
        if "functional" in str(item.fspath):
            item.add_marker(pytest.mark.functional)
        
        # Mark slow tests
        if "performance" in str(item.fspath) or "benchmark" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Mark MCP tests
        if "mcp" in item.name or "mcp" in str(item.fspath):
            item.add_marker(pytest.mark.mcp)
        
        # Mark integration tests
        if "integration" in str(item.fspath) or "end_to_end" in item.name:
            item.add_marker(pytest.mark.integration)