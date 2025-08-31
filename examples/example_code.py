#!/usr/bin/env python3
"""
Example Python code with various refactoring opportunities
This file demonstrates different patterns that the MCP tool can detect
"""

def process_user_registration(user_data, email, password, confirm_password, 
                            phone, address, city, country, postal_code):
    """Long function with multiple refactoring opportunities"""
    
    # Validation block that could be extracted
    if not user_data:
        print("User data is required")
        return False
    
    if not email or '@' not in email:
        print("Valid email is required") 
        return False
        
    if len(password) < 8:
        print("Password must be at least 8 characters")
        return False
        
    if password != confirm_password:
        print("Passwords do not match")
        return False
    
    # Phone validation block
    if phone and not phone.startswith('+'):
        phone = '+' + phone
        
    if phone and len(phone.replace('+', '').replace('-', '').replace(' ', '')) < 10:
        print("Invalid phone number")
        return False
        
    # Address processing block
    full_address = f"{address}, {city}, {country} {postal_code}"
    
    if len(full_address) > 200:
        print("Address too long")
        return False
        
    # Complex database operations
    try:
        # This block could also be extracted
        user_id = generate_user_id()
        
        if check_email_exists(email):
            print("Email already exists")
            return False
            
        # Hash password
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create user record
        user_record = {
            'id': user_id,
            'email': email,
            'password_hash': password_hash,
            'phone': phone,
            'address': full_address,
            'created_at': get_current_timestamp(),
            'verified': False
        }
        
        # Save to database
        save_user_to_database(user_record)
        
        # Send verification email
        send_verification_email(email, user_id)
        
        print(f"User {email} registered successfully with ID {user_id}")
        return True
        
    except Exception as e:
        print(f"Registration failed: {e}")
        return False

def calculate_complex_score(data1, data2, data3, data4, data5, data6, data7, weight1, weight2, weight3):
    """Function with too many parameters"""
    # Complex calculation that has high cyclomatic complexity
    total = 0
    
    if data1 > 0:
        if data1 > 100:
            if weight1 > 0.5:
                total += data1 * weight1 * 1.5
            else:
                total += data1 * weight1
        else:
            if weight1 > 0.3:
                total += data1 * weight1 * 1.2
            else:
                total += data1 * weight1 * 0.8
    
    if data2 > 0:
        if data2 > 50:
            if weight2 > 0.7:
                total += data2 * weight2 * 2.0
            else:
                total += data2 * weight2 * 1.5
        else:
            total += data2 * weight2
            
    if data3 > 0:
        for i in range(data3):
            if i % 2 == 0:
                total += i * 0.1
            else:
                total -= i * 0.05
                
    return total

def unused_function():
    """This function is never called - dead code"""
    return "This should be detected as unused"

unused_variable = "This variable is never used"

def helper_function():
    """Actually used helper function"""
    return 42

def main():
    """Main function that uses some but not all functions"""
    result = helper_function()
    print(f"Result: {result}")

# Helper functions for the example
def generate_user_id():
    import uuid
    return str(uuid.uuid4())

def check_email_exists(email):
    # Simulate database check
    return email in ['admin@example.com', 'test@example.com']

def save_user_to_database(user_record):
    # Simulate database save
    print(f"Saving user to database: {user_record['email']}")

def send_verification_email(email, user_id):
    # Simulate email sending
    print(f"Sending verification email to {email} for user {user_id}")

def get_current_timestamp():
    import datetime
    return datetime.datetime.now().isoformat()

if __name__ == "__main__":
    main()