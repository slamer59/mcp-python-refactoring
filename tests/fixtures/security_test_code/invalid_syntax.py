#!/usr/bin/env python3
"""
Test file with invalid Python syntax for testing error handling in analyzers.
This file intentionally contains syntax errors for testing purposes.
"""

# Missing closing parenthesis
def broken_function(param1, param2:
    return param1 + param2

# Invalid indentation
class BrokenClass:
def method_one(self):
        return "indentation error"

# Unclosed string
def another_broken_function():
    message = "This string is never closed
    return message

# Invalid syntax with missing colon
if True
    print("Missing colon in if statement")

# Incorrect function definition
def 123invalid_name():
    pass

# Mismatched brackets
def mismatched_brackets():
    data = {"key": "value", "another": ["item1", "item2"}
    return data

# This file should trigger syntax error handling in all analyzers