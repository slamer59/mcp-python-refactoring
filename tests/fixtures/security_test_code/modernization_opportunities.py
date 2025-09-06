#!/usr/bin/env python3
"""
Test file containing various modernization opportunities for testing ModernPatternsAnalyzer
This file intentionally uses outdated Python patterns for testing purposes.
"""

import os
import sys
from typing import List, Dict, Any


# FURB106: Use f-strings instead of .format()
def format_message(name, age):
    return "Hello {}, you are {} years old".format(name, age)


# FURB106: Use f-strings instead of % formatting
def old_format_message(name, age):
    return "Hello %s, you are %d years old" % (name, age)


# FURB102: Use enumerate instead of manual index tracking
def process_items_with_index(items):
    result = []
    for i in range(len(items)):
        result.append(f"Item {i}: {items[i]}")
    return result


# FURB101: Use pathlib instead of os.path
def get_file_info(filepath):
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    extension = os.path.splitext(filename)[1]
    size = os.path.getsize(filepath)
    return {
        "dir": directory,
        "name": filename,
        "ext": extension,
        "size": size,
        "full_path": os.path.join(directory, filename)
    }


# FURB104: Use ternary operator for simple if-else
def get_status(is_active):
    if is_active:
        status = "active"
    else:
        status = "inactive"
    return status


# FURB110: Use any() instead of loop returning boolean
def has_negative_numbers(numbers):
    for num in numbers:
        if num < 0:
            return True
    return False


# FURB111: Use all() instead of loop checking all conditions
def all_positive_numbers(numbers):
    for num in numbers:
        if num <= 0:
            return False
    return True


# FURB108: Use dict.get() instead of manual key checking
def get_config_value(config, key, default_value):
    if key in config:
        return config[key]
    else:
        return default_value


# FURB117: Use dict comprehension instead of loop
def create_squared_dict(numbers):
    result = {}
    for num in numbers:
        result[num] = num ** 2
    return result


# FURB118: Use dict comprehension instead of manual loop
def filter_even_numbers_dict(numbers):
    result = {}
    for i, num in enumerate(numbers):
        if num % 2 == 0:
            result[i] = num
    return result


# FURB119: Use zip() for parallel iteration
def combine_lists(list1, list2):
    result = []
    for i in range(min(len(list1), len(list2))):
        result.append((list1[i], list2[i]))
    return result


# FURB120: Use enumerate() for indexed iteration
def process_with_index(items):
    result = []
    for i in range(len(items)):
        result.append(f"{i}: {items[i].upper()}")
    return result


# FURB112: Use next() builtin instead of loop to find first match
def find_first_adult(people):
    for person in people:
        if person.get('age', 0) >= 18:
            return person
    return None


# FURB116: Use isinstance() instead of type() comparison
def check_if_string(value):
    return type(value) == str


# FURB115: Not using context manager for file operations
def read_file_content(filename):
    f = open(filename, 'r')
    content = f.read()
    f.close()
    return content


# FURB105: Use print() instead of sys.stdout.write()
def output_message(message):
    sys.stdout.write(message + '\n')


# FURB103: Not using explicit file mode
def write_to_file(filename, content):
    with open(filename) as f:  # Should specify 'w' mode explicitly
        f.write(content)


# Multiple modernization opportunities in one function
def complex_legacy_function(users_data, config_file):
    """Function with multiple modernization opportunities for comprehensive testing."""
    
    # Should use pathlib
    config_dir = os.path.dirname(config_file)
    config_name = os.path.basename(config_file)
    
    # Should use f-strings
    log_message = "Processing {} users from config {}".format(len(users_data), config_name)
    
    # Should use enumerate
    processed_users = []
    for i in range(len(users_data)):
        user = users_data[i]
        
        # Should use dict.get()
        if 'age' in user:
            age = user['age']
        else:
            age = 0
        
        # Should use ternary operator
        if age >= 18:
            status = "adult"
        else:
            status = "minor"
        
        # Should use isinstance
        if type(user.get('name')) == str:
            name = user['name'].title()
        else:
            name = "Unknown"
        
        # Should use f-strings
        user_info = "User %d: %s (%s)" % (i, name, status)
        processed_users.append(user_info)
    
    # Should use any()
    has_adults = False
    for user in users_data:
        if user.get('age', 0) >= 18:
            has_adults = True
            break
    
    # Should use all()
    all_have_names = True
    for user in users_data:
        if not user.get('name'):
            all_have_names = False
            break
    
    # Should use dict comprehension
    age_mapping = {}
    for i, user in enumerate(users_data):
        age_mapping[i] = user.get('age', 0)
    
    # Should use next()
    first_admin = None
    for user in users_data:
        if user.get('role') == 'admin':
            first_admin = user
            break
    
    # Should use zip()
    names = [u.get('name', '') for u in users_data]
    ages = [u.get('age', 0) for u in users_data]
    combined = []
    for i in range(min(len(names), len(ages))):
        combined.append((names[i], ages[i]))
    
    # Should use context manager and explicit mode
    log_file = open('processing.log', 'w')
    log_file.write(log_message + '\n')
    log_file.close()
    
    # Should use print() instead of sys.stdout.write()
    sys.stdout.write("Processing complete\n")
    
    return {
        "processed": processed_users,
        "has_adults": has_adults,
        "all_have_names": all_have_names,
        "age_mapping": age_mapping,
        "first_admin": first_admin,
        "combined": combined,
        "log_message": log_message
    }


# Additional legacy patterns
class LegacyDataProcessor:
    """Class with multiple modernization opportunities."""
    
    def __init__(self, data_path):
        # Should use pathlib
        self.data_dir = os.path.dirname(data_path)
        self.data_file = os.path.basename(data_path)
        self.full_path = os.path.join(self.data_dir, self.data_file)
    
    def process_data(self, filter_func=None):
        # Should use context manager
        f = open(self.full_path, 'r')
        lines = f.readlines()
        f.close()
        
        # Should use enumerate
        processed = []
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # Should use f-strings
            processed_line = "Line {}: {}".format(i, line)
            
            # Apply filter if provided
            if filter_func:
                # Should use ternary operator
                if filter_func(line):
                    keep = True
                else:
                    keep = False
                
                if keep:
                    processed.append(processed_line)
            else:
                processed.append(processed_line)
        
        return processed
    
    def get_file_stats(self):
        # Should use pathlib
        size = os.path.getsize(self.full_path)
        exists = os.path.exists(self.full_path)
        
        # Should use isinstance
        if type(size) == int and size > 0:
            status = "valid"
        else:
            status = "invalid"
        
        return {
            "size": size,
            "exists": exists,
            "status": status
        }