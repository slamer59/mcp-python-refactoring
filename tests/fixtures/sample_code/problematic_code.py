# Various problematic code patterns for testing

# Function with syntax errors
def broken_function(
    # Missing closing parenthesis and colon
    print("This will not work")
    return "broken"

# Function with too many parameters
def too_many_params(a, b, c, d, e, f, g, h, i, j, k, l):
    """Function with excessive parameters."""
    return a + b + c + d + e + f + g + h + i + j + k + l

# Unused function (dead code)
def never_called_function():
    """This function is never used."""
    return "dead code"

# Function with high cyclomatic complexity
def high_complexity_function(data):
    """Function with excessive branching."""
    result = []
    
    if data:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if 'type' in item:
                        if item['type'] == 'A':
                            if 'value' in item:
                                if item['value'] > 0:
                                    result.append(item['value'] * 2)
                                else:
                                    result.append(0)
                            else:
                                result.append(-1)
                        elif item['type'] == 'B':
                            if 'value' in item:
                                if item['value'] < 0:
                                    result.append(abs(item['value']))
                                else:
                                    result.append(item['value'])
                            else:
                                result.append(1)
                        else:
                            result.append(None)
                    else:
                        result.append("no_type")
                else:
                    result.append("not_dict")
        else:
            result.append("not_list")
    else:
        result.append("no_data")
    
    return result

# Function that should use the unused function but doesn't
def main_function():
    """Main function that doesn't use all available functions."""
    result = too_many_params(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    complex_result = high_complexity_function([{'type': 'A', 'value': 5}])
    return result + sum(complex_result)