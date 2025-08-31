#!/usr/bin/env python3
"""Test script for the MCP refactoring tool"""

import json
from src.mcp_refactoring_assistant.server import EnhancedRefactoringAnalyzer

def test_tool():
    """Test the refactoring analyzer with example code"""
    
    # Read example code
    with open('examples/example_code.py', 'r') as f:
        content = f.read()
    
    # Initialize analyzer
    analyzer = EnhancedRefactoringAnalyzer()
    
    print("🔍 Testing MCP Python Refactoring Tool\n")
    
    # Test 1: Full analysis
    print("=" * 50)
    print("TEST 1: Full File Analysis")
    print("=" * 50)
    
    guidance = analyzer.analyze_file('example_code.py', content)
    
    print(f"Found {len(guidance)} refactoring opportunities:\n")
    
    for i, g in enumerate(guidance, 1):
        print(f"{i}. {g.issue_type.upper()} [{g.severity}]")
        print(f"   📍 Location: {g.location}")
        print(f"   📝 Description: {g.description}")
        print(f"   💡 Benefits: {', '.join(g.benefits[:2])}...")
        
        if g.extractable_blocks:
            print(f"   🎯 Extractable Blocks: {len(g.extractable_blocks)}")
            for j, block in enumerate(g.extractable_blocks[:1], 1):  # Show first block
                print(f"      Block {j}: {block.suggested_name} (lines {block.start_line}-{block.end_line})")
        print()
    
    # Test 2: JSON output simulation (like MCP would return)
    print("=" * 50)
    print("TEST 2: MCP-Style JSON Output")  
    print("=" * 50)
    
    result = {
        "analysis_summary": {
            "total_issues_found": len(guidance),
            "critical_issues": len([g for g in guidance if g.severity == "critical"]),
            "high_priority": len([g for g in guidance if g.severity == "high"]),
            "medium_priority": len([g for g in guidance if g.severity == "medium"]),
            "low_priority": len([g for g in guidance if g.severity == "low"])
        },
        "refactoring_guidance": [g.to_dict() for g in guidance[:2]],  # First 2 for brevity
        "tools_used": {
            "rope": True,  # Would be dynamic
            "radon": True,
            "vulture": True
        }
    }
    
    print(json.dumps(result, indent=2))
    
    # Test 3: Specific function analysis
    print("\n" + "=" * 50)
    print("TEST 3: Extract Function Opportunities")
    print("=" * 50)
    
    extraction_guidance = [g for g in guidance if g.issue_type == "extract_function"]
    
    if extraction_guidance:
        print(f"Found {len(extraction_guidance)} functions ready for extraction:\n")
        for g in extraction_guidance:
            print(f"📋 {g.location}")
            print("✂️  Extraction Steps:")
            for step in g.precise_steps[:3]:
                print(f"   {step}")
            print("   ... (and more steps)")
            print()
    else:
        print("No extract function opportunities detected in this example.")
        print("(Functions may be under the 20-line threshold)")
    
    print("\n✅ Testing completed successfully!")
    print("\nThis demonstrates how an LLM would interact with the MCP tool:")
    print("1. LLM calls analyze_python_file")  
    print("2. Tool returns structured JSON with precise guidance")
    print("3. LLM interprets results and guides user step-by-step")
    print("4. User follows exact cut/paste instructions")

if __name__ == "__main__":
    test_tool()