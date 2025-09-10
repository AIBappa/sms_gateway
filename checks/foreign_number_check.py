import json
import re

async def validate_foreign_number_check(sms, pool):
    """
    Validates that sender number starts with allowed country codes.
    Returns:
    - 1: pass (valid country code)
    - 2: fail (invalid country code or format)
    """
    try:
        # Get allowed country codes from system_settings
        async with pool.acquire() as conn:
            allowed_codes_str = await conn.fetchval(
                "SELECT setting_value FROM system_settings WHERE setting_key = 'allowed_country_codes'"
            )
            foreign_validation_enabled = await conn.fetchval(
                "SELECT setting_value FROM system_settings WHERE setting_key = 'foreign_number_validation'"
            )
        
        # If foreign number validation is disabled, pass all
        if foreign_validation_enabled.lower() == 'false':
            return 1
        
        allowed_codes = json.loads(allowed_codes_str)
        sender_number = sms.sender_number.strip()
        
        # Remove any non-digit characters from the beginning
        clean_number = re.sub(r'^[^\d]*', '', sender_number)
        
        # Check if number starts with any allowed country code
        for code in allowed_codes:
            if clean_number.startswith(code):
                return 1  # pass
        
        return 2  # fail - no matching country code
        
    except Exception as e:
        # Log error and fail safely
        print(f"Error in foreign_number_check: {e}")
        return 2  # fail on error
