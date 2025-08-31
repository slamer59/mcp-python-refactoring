# Simple, clean functions for testing baseline behavior

def add_numbers(a, b):
    """Add two numbers together."""
    return a + b

def greet_user(name):
    """Return a greeting for the user."""
    return f"Hello, {name}!"

def calculate_area(width, height):
    """Calculate the area of a rectangle."""
    if width <= 0 or height <= 0:
        raise ValueError("Dimensions must be positive")
    return width * height

def is_even(number):
    """Check if a number is even."""
    return number % 2 == 0