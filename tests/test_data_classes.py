#!/usr/bin/env python3
"""
Tests for core data classes: ExtractableBlock and RefactoringGuidance
"""

import pytest
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_refactoring_assistant.models import ExtractableBlock, RefactoringGuidance


class TestExtractableBlock:
    """Test ExtractableBlock data class"""

    def test_extractable_block_creation(self):
        """Test ExtractableBlock object creation"""
        block = ExtractableBlock(
            start_line=10,
            end_line=20,
            content="def test_func():\n    return True",
            variables_used=["var1", "var2"],
            variables_modified=["result"],
            suggested_name="test_function",
            description="Test function block",
            complexity_score=2.5,
            extraction_type="function"
        )
        
        assert block.start_line == 10
        assert block.end_line == 20
        assert block.content == "def test_func():\n    return True"
        assert block.variables_used == ["var1", "var2"]
        assert block.variables_modified == ["result"]
        assert block.suggested_name == "test_function"
        assert block.description == "Test function block"
        assert block.complexity_score == 2.5
        assert block.extraction_type == "function"

    def test_extractable_block_defaults(self):
        """Test ExtractableBlock with default values"""
        block = ExtractableBlock(
            start_line=5,
            end_line=15,
            content="simple code",
            variables_used=[],
            variables_modified=[],
            suggested_name="simple_func",
            description="Simple block"
        )
        
        # Test default values
        assert block.complexity_score == 0.0
        assert block.extraction_type == "function"

    def test_extractable_block_to_dict(self):
        """Test ExtractableBlock to_dict method"""
        block = ExtractableBlock(
            start_line=1,
            end_line=5,
            content="test",
            variables_used=["x"],
            variables_modified=["y"],
            suggested_name="test_func",
            description="Test",
            complexity_score=1.0,
            extraction_type="method"
        )
        
        result = block.to_dict()
        expected = block.model_dump()
        
        assert result == expected
        assert isinstance(result, dict)
        assert result["start_line"] == 1
        assert result["end_line"] == 5
        assert result["extraction_type"] == "method"

    def test_extractable_block_edge_cases(self):
        """Test ExtractableBlock edge cases"""
        # Empty variables lists
        block = ExtractableBlock(
            start_line=1,
            end_line=1,
            content="",
            variables_used=[],
            variables_modified=[],
            suggested_name="",
            description=""
        )
        
        assert len(block.variables_used) == 0
        assert len(block.variables_modified) == 0
        assert block.content == ""
        assert block.suggested_name == ""


class TestRefactoringGuidance:
    """Test RefactoringGuidance data class"""

    def test_refactoring_guidance_creation(self):
        """Test RefactoringGuidance object creation"""
        guidance = RefactoringGuidance(
            issue_type="high_complexity",
            severity="high",
            location="Function 'complex_func' at line 50",
            description="Function has high cyclomatic complexity: 15",
            benefits=["Improved readability", "Easier testing"],
            precise_steps=["1. Extract complex conditions", "2. Add unit tests"]
        )
        
        assert guidance.issue_type == "high_complexity"
        assert guidance.severity == "high"
        assert guidance.location == "Function 'complex_func' at line 50"
        assert guidance.description == "Function has high cyclomatic complexity: 15"
        assert guidance.benefits == ["Improved readability", "Easier testing"]
        assert guidance.precise_steps == ["1. Extract complex conditions", "2. Add unit tests"]
        
        # Test default None values
        assert guidance.code_snippet is None
        assert guidance.extractable_blocks is None
        assert guidance.rope_suggestions is None
        assert guidance.metrics is None

    def test_refactoring_guidance_with_optional_fields(self):
        """Test RefactoringGuidance with optional fields"""
        block = ExtractableBlock(
            start_line=10,
            end_line=15,
            content="test code",
            variables_used=["x"],
            variables_modified=["y"],
            suggested_name="extract_func",
            description="Test block"
        )
        
        guidance = RefactoringGuidance(
            issue_type="extract_function",
            severity="medium",
            location="Function 'long_func' lines 10-30",
            description="Long function with extractable blocks",
            benefits=["Better readability"],
            precise_steps=["Extract block"],
            code_snippet="def long_func():\n    pass",
            extractable_blocks=[block],
            rope_suggestions={"rename": "new_name"},
            metrics={"complexity": 8}
        )
        
        assert guidance.code_snippet == "def long_func():\n    pass"
        assert len(guidance.extractable_blocks) == 1
        assert guidance.extractable_blocks[0] == block
        assert guidance.rope_suggestions == {"rename": "new_name"}
        assert guidance.metrics == {"complexity": 8}

    def test_refactoring_guidance_to_dict_no_blocks(self):
        """Test RefactoringGuidance to_dict without extractable blocks"""
        guidance = RefactoringGuidance(
            issue_type="dead_code",
            severity="low",
            location="Line 25",
            description="Unused variable",
            benefits=["Cleaner code"],
            precise_steps=["Remove unused variable"]
        )
        
        result = guidance.to_dict()
        expected = guidance.model_dump()
        
        assert result == expected
        assert isinstance(result, dict)
        assert "extractable_blocks" not in result or result["extractable_blocks"] is None

    def test_refactoring_guidance_to_dict_with_blocks(self):
        """Test RefactoringGuidance to_dict with extractable blocks"""
        block1 = ExtractableBlock(
            start_line=5,
            end_line=10,
            content="block1",
            variables_used=["a"],
            variables_modified=["b"],
            suggested_name="func1",
            description="Block 1"
        )
        
        block2 = ExtractableBlock(
            start_line=15,
            end_line=20,
            content="block2",
            variables_used=["c"],
            variables_modified=["d"],
            suggested_name="func2",
            description="Block 2"
        )
        
        guidance = RefactoringGuidance(
            issue_type="extract_function",
            severity="medium",
            location="Function test",
            description="Multiple blocks",
            benefits=["Better structure"],
            precise_steps=["Extract blocks"],
            extractable_blocks=[block1, block2]
        )
        
        result = guidance.to_dict()
        
        assert "extractable_blocks" in result
        assert len(result["extractable_blocks"]) == 2
        assert result["extractable_blocks"][0] == block1.to_dict()
        assert result["extractable_blocks"][1] == block2.to_dict()
        
        # Ensure blocks were properly converted to dicts
        for block_dict in result["extractable_blocks"]:
            assert isinstance(block_dict, dict)
            assert "start_line" in block_dict
            assert "end_line" in block_dict

    def test_refactoring_guidance_severity_levels(self):
        """Test different severity levels"""
        severities = ["low", "medium", "high", "critical"]
        
        for severity in severities:
            guidance = RefactoringGuidance(
                issue_type="test",
                severity=severity,
                location="test",
                description="test",
                benefits=["test"],
                precise_steps=["test"]
            )
            assert guidance.severity == severity

    def test_refactoring_guidance_empty_collections(self):
        """Test RefactoringGuidance with empty collections"""
        guidance = RefactoringGuidance(
            issue_type="test",
            severity="low",
            location="test",
            description="test",
            benefits=[],  # Empty benefits
            precise_steps=[],  # Empty steps
            extractable_blocks=[]  # Empty blocks
        )
        
        assert guidance.benefits == []
        assert guidance.precise_steps == []
        assert guidance.extractable_blocks == []
        
        # to_dict should handle empty blocks list
        result = guidance.to_dict()
        assert result["extractable_blocks"] == []


if __name__ == "__main__":
    pytest.main([__file__])