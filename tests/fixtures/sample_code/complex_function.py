# Complex function with multiple refactoring opportunities

def process_user_data(user_id, name, email, age, preferences, settings, metadata, flags, options, config):
    """Process user data with multiple validation and transformation steps."""
    
    # Input validation - could be extracted
    if not user_id or not isinstance(user_id, (int, str)):
        raise ValueError("Invalid user ID")
    if not name or len(name.strip()) == 0:
        raise ValueError("Name cannot be empty")
    if not email or "@" not in email:
        raise ValueError("Invalid email format")
    if age is not None and (not isinstance(age, int) or age < 0 or age > 150):
        raise ValueError("Invalid age")
    
    # Data cleaning - could be extracted
    cleaned_name = name.strip().title()
    cleaned_email = email.strip().lower()
    
    # Preference processing - could be extracted
    processed_preferences = {}
    if preferences:
        for key, value in preferences.items():
            if key in ['theme', 'language', 'timezone']:
                if value and len(str(value).strip()) > 0:
                    processed_preferences[key] = str(value).strip()
    
    # Settings validation - could be extracted
    validated_settings = {}
    if settings:
        for setting_key, setting_value in settings.items():
            if setting_key in ['notifications', 'privacy', 'security']:
                if isinstance(setting_value, bool):
                    validated_settings[setting_key] = setting_value
                elif isinstance(setting_value, str) and setting_value.lower() in ['true', 'false']:
                    validated_settings[setting_key] = setting_value.lower() == 'true'
    
    # Metadata processing - could be extracted
    processed_metadata = {}
    if metadata:
        for meta_key, meta_value in metadata.items():
            if meta_key.startswith('user_'):
                processed_metadata[meta_key] = meta_value
    
    # Complex business logic - could be extracted
    user_category = 'standard'
    if age is not None:
        if age < 18:
            user_category = 'minor'
        elif age >= 65:
            user_category = 'senior'
        elif 18 <= age < 25:
            user_category = 'young_adult'
        elif 25 <= age < 40:
            user_category = 'adult'
        elif 40 <= age < 65:
            user_category = 'middle_aged'
    
    # Flag processing - could be extracted
    active_flags = []
    if flags:
        for flag in flags:
            if isinstance(flag, str) and flag.strip():
                flag_name = flag.strip().lower()
                if flag_name in ['premium', 'verified', 'beta_tester', 'early_adopter']:
                    active_flags.append(flag_name)
    
    # Result compilation
    result = {
        'user_id': user_id,
        'name': cleaned_name,
        'email': cleaned_email,
        'age': age,
        'category': user_category,
        'preferences': processed_preferences,
        'settings': validated_settings,
        'metadata': processed_metadata,
        'flags': active_flags,
        'processed_at': 'timestamp_would_go_here'
    }
    
    # Final validation
    if not result['name'] or not result['email']:
        raise ValueError("Processing failed: missing required fields")
    
    return result