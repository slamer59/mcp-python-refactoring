#!/usr/bin/env python3
"""
Example Python code with various refactoring opportunities
This file demonstrates different patterns that the MCP tool can detect
"""

import hashlib
import datetime
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserRegistrationData:
    """Data class for user registration information"""
    user_data: dict
    email: str
    password: str
    confirm_password: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_user_data(user_data: dict) -> None:
    """Validate basic user data"""
    if not user_data:
        raise ValidationError("User data is required")


def validate_email(email: str) -> None:
    """Validate email format and availability"""
    if not email or '@' not in email:
        raise ValidationError("Valid email is required")
    
    if check_email_exists(email):
        raise ValidationError("Email already exists")


def validate_password(password: str, confirm_password: str) -> None:
    """Validate password requirements"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")
        
    if password != confirm_password:
        raise ValidationError("Passwords do not match")


def validate_and_format_phone(phone: Optional[str]) -> Optional[str]:
    """Validate and format phone number"""
    if not phone:
        return None
        
    formatted_phone = phone if phone.startswith('+') else '+' + phone
    clean_phone = formatted_phone.replace('+', '').replace('-', '').replace(' ', '')
    
    if len(clean_phone) < 10:
        raise ValidationError("Invalid phone number")
        
    return formatted_phone


def validate_and_format_address(address: str, city: str, country: str, postal_code: str) -> str:
    """Validate and format full address"""
    full_address = f"{address}, {city}, {country} {postal_code}"
    
    if len(full_address) > 200:
        raise ValidationError("Address too long")
        
    return full_address


def create_user_record(registration_data: UserRegistrationData, user_id: str, phone: Optional[str], full_address: str) -> dict:
    """Create user record dictionary"""
    password_hash = hashlib.sha256(registration_data.password.encode()).hexdigest()
    
    return {
        'id': user_id,
        'email': registration_data.email,
        'password_hash': password_hash,
        'phone': phone,
        'address': full_address,
        'created_at': get_current_timestamp(),
        'verified': False
    }


def process_user_registration(registration_data: UserRegistrationData) -> bool:
    """Process user registration with improved structure"""
    try:
        # Validation phase
        validate_user_data(registration_data.user_data)
        validate_email(registration_data.email)
        validate_password(registration_data.password, registration_data.confirm_password)
        
        phone = validate_and_format_phone(registration_data.phone)
        full_address = validate_and_format_address(
            registration_data.address, 
            registration_data.city, 
            registration_data.country, 
            registration_data.postal_code
        )
        
        # Registration phase
        user_id = generate_user_id()
        user_record = create_user_record(registration_data, user_id, phone, full_address)
        
        # Persistence and notification phase
        save_user_to_database(user_record)
        send_verification_email(registration_data.email, user_id)
        
        print(f"User {registration_data.email} registered successfully with ID {user_id}")
        return True
        
    except ValidationError as e:
        print(f"Validation failed: {e}")
        return False
    except Exception as e:
        print(f"Registration failed: {e}")
        return False

@dataclass
class ScoreCalculationData:
    """Data class for score calculation parameters"""
    data1: float = 0
    data2: float = 0
    data3: int = 0
    data4: float = 0
    data5: float = 0
    data6: float = 0
    data7: float = 0
    weight1: float = 0
    weight2: float = 0
    weight3: float = 0


def calculate_data1_score(data1: float, weight1: float) -> float:
    """Calculate score for data1 with weight1"""
    if data1 <= 0:
        return 0
    
    if data1 > 100:
        multiplier = 1.5 if weight1 > 0.5 else 1.0
    else:
        multiplier = 1.2 if weight1 > 0.3 else 0.8
    
    return data1 * weight1 * multiplier


def calculate_data2_score(data2: float, weight2: float) -> float:
    """Calculate score for data2 with weight2"""
    if data2 <= 0:
        return 0
    
    if data2 > 50:
        multiplier = 2.0 if weight2 > 0.7 else 1.5
        return data2 * weight2 * multiplier
    else:
        return data2 * weight2


def calculate_data3_score(data3: int) -> float:
    """Calculate score for data3 using alternating pattern"""
    if data3 <= 0:
        return 0
    
    total = 0
    for i in range(data3):
        if i % 2 == 0:
            total += i * 0.1
        else:
            total -= i * 0.05
    
    return total


def calculate_complex_score(score_data: ScoreCalculationData) -> float:
    """Calculate complex score with improved structure"""
    total = 0
    
    total += calculate_data1_score(score_data.data1, score_data.weight1)
    total += calculate_data2_score(score_data.data2, score_data.weight2)
    total += calculate_data3_score(score_data.data3)
    
    return total


def helper_function():
    """Actually used helper function"""
    return 42

def main():
    """Main function that uses some but not all functions"""
    result = helper_function()
    print(f"Result: {result}")

def generate_user_id() -> str:
    """Generate unique user ID"""
    return str(uuid.uuid4())


def check_email_exists(email: str) -> bool:
    """Simulate database check for existing email"""
    return email in ['admin@example.com', 'test@example.com']


def save_user_to_database(user_record: dict) -> None:
    """Simulate database save operation"""
    print(f"Saving user to database: {user_record['email']}")


def send_verification_email(email: str, user_id: str) -> None:
    """Simulate email sending"""
    print(f"Sending verification email to {email} for user {user_id}")


def get_current_timestamp() -> str:
    """Get current timestamp as ISO string"""
    return datetime.datetime.now().isoformat()

if __name__ == "__main__":
    main()