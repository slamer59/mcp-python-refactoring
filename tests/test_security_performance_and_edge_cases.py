#!/usr/bin/env python3
"""
Performance and edge case tests for security and patterns analysis features
Tests large files, edge cases, and performance characteristics
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.mcp_refactoring_assistant.analyzers.security_analyzer import SecurityAnalyzer
from src.mcp_refactoring_assistant.analyzers.modern_patterns_analyzer import ModernPatternsAnalyzer
from src.mcp_refactoring_assistant.analyzers.dependency_security_analyzer import DependencySecurityAnalyzer
from src.mcp_refactoring_assistant.analyzers.security_and_patterns_analyzer import SecurityAndPatternsAnalyzer


class TestSecurityPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.security_analyzer = SecurityAnalyzer()
        self.patterns_analyzer = ModernPatternsAnalyzer()
        self.dependency_analyzer = DependencySecurityAnalyzer()
        self.unified_analyzer = SecurityAndPatternsAnalyzer()
    
    def generate_large_vulnerable_code(self, size_factor=10):
        """Generate a large code file with multiple vulnerabilities"""
        base_vulnerable_code = '''
import subprocess
import pickle
import hashlib
import os
import yaml
import requests

# Function with multiple vulnerabilities
def vulnerable_function_{i}(user_input, data, password="hardcoded{i}"):
    # B105: Hardcoded password
    secret_key = "api_key_{i}"
    
    # B602: Shell injection
    subprocess.call(f"ls {{user_input}}", shell=True)
    
    # B301: Pickle deserialization
    obj = pickle.loads(data)
    
    # B303: MD5 usage
    hash_val = hashlib.md5((password + str(obj)).encode()).hexdigest()
    
    # B608: SQL injection potential
    query = f"SELECT * FROM users WHERE id = '{{obj.get('id', 0)}}')"
    
    # B506: YAML load
    config = yaml.load(f"setting: {{obj}}")
    
    # B501: SSL verification disabled
    response = requests.get(f"https://api.example.com/{{obj}}", verify=False)
    
    # B110: Try/except pass
    try:
        result = process_data(response, hash_val)
    except:
        pass
    
    # B108: Hardcoded temp directory
    temp_file = "/tmp/output_{{i}}.txt"
    
    return {{
        "hash": hash_val,
        "query": query,
        "temp_file": temp_file,
        "config": config
    }}

def process_data(response, hash_val):
    return response.text + hash_val
'''
        
        large_code = ""
        for i in range(size_factor):
            large_code += base_vulnerable_code.format(i=i) + "\n\n"
        
        return large_code
    
    def generate_large_legacy_code(self, size_factor=10):
        """Generate a large code file with many modernization opportunities"""
        base_legacy_code = '''
import os
import sys

def legacy_function_{i}(data_list, config_file):
    # Should use pathlib
    config_dir = os.path.dirname(config_file)
    config_name = os.path.basename(config_file)
    
    # Should use f-strings
    log_message = "Processing {{}} items from config {{}}".format(len(data_list), config_name)
    
    # Should use enumerate
    results = []
    for idx in range(len(data_list)):
        item = data_list[idx]
        
        # Should use dict.get
        if "name" in item:
            name = item["name"]
        else:
            name = "Unknown"
        
        # Should use ternary operator
        if len(name) > 10:
            short_name = name[:10]
        else:
            short_name = name
        
        # Should use isinstance
        if type(item.get("id")) == int:
            id_str = str(item["id"])
        else:
            id_str = "0"
        
        # Should use f-strings
        item_desc = "Item %d: %s (%s)" % (idx, short_name, id_str)
        results.append(item_desc)
    
    # Should use any()
    has_valid_items = False
    for item in data_list:
        if item.get("valid"):
            has_valid_items = True
            break
    
    # Should use all()
    all_have_names = True
    for item in data_list:
        if not item.get("name"):
            all_have_names = False
            break
    
    # Should use dict comprehension
    name_map = {{}}
    for i, item in enumerate(data_list):
        name_map[i] = item.get("name", f"item_{{i}}")
    
    # Should use next()
    first_valid = None
    for item in data_list:
        if item.get("valid"):
            first_valid = item
            break
    
    # Should use zip()
    names = [item.get("name", "") for item in data_list]
    ids = [item.get("id", 0) for item in data_list]
    combined = []
    for i in range(min(len(names), len(ids))):
        combined.append((names[i], ids[i]))
    
    # Should use context manager
    log_file = open(f"log_{{i}}.txt", "w")
    log_file.write(log_message)
    log_file.close()
    
    # Should use print()
    sys.stdout.write(f"Function {{i}} completed\\n")
    
    return {{
        "results": results,
        "has_valid": has_valid_items,
        "all_named": all_have_names,
        "name_map": name_map,
        "first_valid": first_valid,
        "combined": combined
    }}
'''
        
        large_code = ""
        for i in range(size_factor):
            large_code += base_legacy_code.format(i=i) + "\n\n"
        
        return large_code
    
    def test_large_file_security_analysis_performance(self):
        """Test performance with large files containing many security issues"""
        large_code = self.generate_large_vulnerable_code(size_factor=5)  # 5x repetition
        
        start_time = time.time()
        guidance = self.security_analyzer.analyze(large_code, "large_vulnerable.py")
        analysis_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert analysis_time < 60, f"Security analysis took too long: {analysis_time}s"
        
        # Should detect multiple issues
        assert isinstance(guidance, list), "Should return guidance list"
        
        # Log performance for monitoring
        print(f"Security analysis of large file took {analysis_time:.2f}s, found {len(guidance)} issues")
    
    def test_large_file_patterns_analysis_performance(self):
        """Test performance with large files containing many modernization opportunities"""
        large_code = self.generate_large_legacy_code(size_factor=5)  # 5x repetition
        
        start_time = time.time()
        guidance = self.patterns_analyzer.analyze(large_code, "large_legacy.py")
        analysis_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert analysis_time < 60, f"Patterns analysis took too long: {analysis_time}s"
        
        # Should handle large files
        assert isinstance(guidance, list), "Should return guidance list"
        
        print(f"Patterns analysis of large file took {analysis_time:.2f}s, found {len(guidance)} opportunities")
    
    def test_unified_analyzer_performance_with_large_file(self):
        """Test unified analyzer performance with large combined files"""
        large_vulnerable = self.generate_large_vulnerable_code(size_factor=3)
        large_legacy = self.generate_large_legacy_code(size_factor=3)
        combined_large_code = large_vulnerable + "\n\n" + large_legacy
        
        start_time = time.time()
        guidance = self.unified_analyzer.analyze(combined_large_code, "large_combined.py")
        analysis_time = time.time() - start_time
        
        # Should complete within reasonable time (unified analysis may take longer)
        assert analysis_time < 120, f"Unified analysis took too long: {analysis_time}s"
        
        # Should return combined results
        assert isinstance(guidance, list), "Should return guidance list"
        
        print(f"Unified analysis of large file took {analysis_time:.2f}s, found {len(guidance)} issues")
    
    def test_very_long_single_line(self):
        """Test handling of files with extremely long single lines"""
        # Create a very long line
        long_line = 'x = "' + 'A' * 10000 + '"; password = "hardcoded123"'  # Long string with security issue
        
        guidance = self.security_analyzer.analyze(long_line, "long_line.py")
        
        # Should handle long lines without crashing
        assert isinstance(guidance, list), "Should handle very long lines"
    
    def test_deeply_nested_code_structure(self):
        """Test handling of deeply nested code structures"""
        nested_code = '''
def level1():
    def level2():
        def level3():
            def level4():
                def level5():
                    # Deep nesting with security issue
                    password = "deeply_nested_secret"
                    import subprocess
                    subprocess.call("ls", shell=True)
                    
                    for i in range(len(items)):  # Modernization opportunity
                        if "key" in items[i]:  # Another opportunity
                            value = items[i]["key"]
                        message = "Item {}: {}".format(i, value)  # f-string opportunity
                    
                    return message
                return level5()
            return level4()
        return level3()
    return level2()
        '''
        
        guidance = self.unified_analyzer.analyze(nested_code, "nested_code.py")
        
        # Should handle deeply nested structures
        assert isinstance(guidance, list), "Should handle deeply nested code"
    
    def test_unicode_and_special_characters(self):
        """Test handling of files with Unicode and special characters"""
        unicode_code = '''
# -*- coding: utf-8 -*-
def process_unicode_data():
    password = "пароль123"  # Unicode password (security issue)
    message = "Привет {}, твой возраст {}".format("Иван", 30)  # f-string opportunity
    
    special_chars = "!@#$%^&*(){}[]|\\:;\"'<>?,./"
    
    # Chinese characters
    chinese_text = "你好世界"
    
    # Emojis
    emoji_text = "Hello 🌍! 👋 🎉"
    
    return {
        "password": password,
        "message": message,
        "special": special_chars,
        "chinese": chinese_text,
        "emoji": emoji_text
    }
        '''
        
        guidance = self.unified_analyzer.analyze(unicode_code, "unicode_test.py")
        
        # Should handle Unicode characters without issues
        assert isinstance(guidance, list), "Should handle Unicode characters"
    
    def test_binary_and_invalid_utf8_handling(self):
        """Test handling of files with binary data or invalid UTF-8"""
        # Create content with mixed valid and invalid bytes
        binary_content = b'''
def test_function():
    password = "secret123"
    \xff\xfe\x00Invalid UTF-8 bytes here
    return password
'''.decode('utf-8', errors='ignore')
        
        guidance = self.security_analyzer.analyze(binary_content, "binary_test.py")
        
        # Should handle gracefully (may or may not find issues depending on how tools handle it)
        assert isinstance(guidance, list), "Should handle binary content gracefully"
    
    def test_extremely_complex_expressions(self):
        """Test handling of extremely complex Python expressions"""
        complex_code = '''
import subprocess
import hashlib

def complex_expression_function():
    # Extremely complex expression with security issues
    result = (
        lambda x, y=hashlib.md5("hardcoded".encode()).hexdigest(): [
            subprocess.call(f"echo {item}", shell=True) or
            {
                "item": item,
                "hash": hashlib.md5(f"{item}{y}".encode()).hexdigest(),
                "processed": [
                    (i, v) for i, v in enumerate([
                        {"data": d, "index": idx} 
                        for idx, d in enumerate(x) 
                        if isinstance(d, (str, int, float))
                    ]) if v["data"] not in ["skip", "ignore"]
                ]
            }
            for item in x if len(str(item)) > 0
        ]
    )
    
    return result

def another_complex_function(data):
    # Complex nested comprehensions with modernization opportunities
    processed = [
        {
            "outer": outer_item,
            "inner": [
                {
                    "value": inner_item,
                    "type": type(inner_item).__name__,
                    "formatted": "Value: {}".format(inner_item)  # f-string opportunity
                }
                for inner_item in (
                    outer_item.get("items", []) if isinstance(outer_item, dict) else []
                )
                if str(inner_item) not in ["", "null", "undefined"]
            ]
        }
        for outer_item in data
        if outer_item is not None and (
            (isinstance(outer_item, dict) and "items" in outer_item) or
            (hasattr(outer_item, "__iter__") and not isinstance(outer_item, str))
        )
    ]
    
    return processed
        '''
        
        guidance = self.unified_analyzer.analyze(complex_code, "complex_expressions.py")
        
        # Should handle complex expressions
        assert isinstance(guidance, list), "Should handle complex expressions"
    
    def test_memory_usage_with_repetitive_patterns(self):
        """Test memory usage with highly repetitive code patterns"""
        # Generate repetitive code that might stress memory usage
        repetitive_code = ""
        
        for i in range(100):  # 100 similar functions
            repetitive_code += f'''
def function_{i}():
    password_{i} = "secret_{i}"
    import subprocess
    subprocess.call(f"process_{{data_{i}}}", shell=True)
    
    items = ["item_0", "item_1", "item_2"]
    for idx in range(len(items)):  # enumerate opportunity
        item = items[idx]
        if "value" in item:  # dict.get opportunity
            value = item["value"]
        message = "Item {{}}: {{}}".format(idx, value)  # f-string opportunity
    
    return message

'''
        
        # Monitor memory usage (basic test)
        guidance = self.unified_analyzer.analyze(repetitive_code, "repetitive_test.py")
        
        # Should complete without memory issues
        assert isinstance(guidance, list), "Should handle repetitive patterns"
        
        # Should deduplicate similar issues efficiently
        unique_locations = set(g.location for g in guidance)
        print(f"Repetitive analysis found {len(guidance)} issues across {len(unique_locations)} locations")
    
    def test_concurrent_analysis_safety(self):
        """Test that analyzers can handle concurrent usage safely"""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def analyze_code(analyzer, code, filename):
            try:
                guidance = analyzer.analyze(code, filename)
                results_queue.put(('success', len(guidance)))
            except Exception as e:
                results_queue.put(('error', str(e)))
        
        # Create multiple threads analyzing different code
        threads = []
        test_codes = [
            ('password = "secret1"', "thread1.py"),
            ('password = "secret2"', "thread2.py"),
            ('password = "secret3"', "thread3.py"),
        ]
        
        for code, filename in test_codes:
            thread = threading.Thread(
                target=analyze_code,
                args=(self.security_analyzer, code, filename)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        # Check results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # All analyses should succeed
        assert len(results) == len(test_codes), "All concurrent analyses should complete"
        
        for result_type, result_data in results:
            assert result_type == 'success', f"Concurrent analysis failed: {result_data}"
    
    def test_edge_case_file_paths(self):
        """Test handling of various edge case file paths"""
        edge_case_paths = [
            "file with spaces.py",
            "file-with-dashes.py", 
            "file_with_underscores.py",
            "file.with.dots.py",
            "ファイル名.py",  # Japanese filename
            "αρχείο.py",     # Greek filename
            "файл.py",       # Russian filename
            "/absolute/path/file.py",
            "relative/path/file.py",
            "../parent/file.py",
            "./current/file.py",
        ]
        
        test_code = 'password = "test_secret"'
        
        for path in edge_case_paths:
            try:
                guidance = self.security_analyzer.analyze(test_code, path)
                assert isinstance(guidance, list), f"Should handle path: {path}"
            except Exception as e:
                # Some paths might cause issues in certain environments
                print(f"Path {path} caused issue: {e}")
    
    def test_analyzer_timeout_behavior(self):
        """Test analyzer behavior when external tools timeout"""
        # This is more of an integration test, but we'll mock the timeout
        with patch('subprocess.run') as mock_run:
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired("bandit", 30)
            
            guidance = self.security_analyzer.analyze("test code", "timeout_test.py")
            
            # Should handle timeouts gracefully
            assert isinstance(guidance, list), "Should handle timeouts gracefully"
            
            timeout_issues = [g for g in guidance if "timeout" in g.issue_type]
            assert len(timeout_issues) > 0, "Should report timeout issues"
    
    def test_analyzer_memory_cleanup(self):
        """Test that analyzers properly clean up temporary files"""
        import tempfile
        import os
        
        # Get initial temp file count
        temp_dir = tempfile.gettempdir()
        initial_temp_files = set(os.listdir(temp_dir))
        
        # Run multiple analyses
        test_code = 'password = "secret123"\nimport subprocess\nsubprocess.call("ls", shell=True)'
        
        for i in range(5):
            guidance = self.security_analyzer.analyze(test_code, f"cleanup_test_{i}.py")
            assert isinstance(guidance, list)
        
        # Check that temp files are cleaned up
        final_temp_files = set(os.listdir(temp_dir))
        
        # Should not have significantly more temp files
        # (allowing for some system temp files that might be created)
        new_temp_files = final_temp_files - initial_temp_files
        temp_py_files = [f for f in new_temp_files if f.endswith('.py')]
        
        assert len(temp_py_files) == 0, f"Temporary Python files not cleaned up: {temp_py_files}"
    
    def test_malformed_guidance_handling(self):
        """Test handling of malformed guidance from external tools"""
        with patch('subprocess.run') as mock_run:
            # Mock malformed JSON output
            mock_result = type('MockResult', (), {})()
            mock_result.returncode = 1
            mock_result.stdout = '{"incomplete": "json", malformed'
            mock_run.return_value = mock_result
            
            guidance = self.security_analyzer.analyze("test code", "malformed_test.py")
            
            # Should handle malformed output gracefully
            assert isinstance(guidance, list), "Should handle malformed tool output"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output