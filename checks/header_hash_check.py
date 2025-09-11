import os
import hmac
import hashlib
import re

async def validate_header_hash_check(sms, pool):
    """
    Combined header and hash validation check.
    Validates SMS message format with header and hash components.
    Expected format: HEADER MOBILE_NUMBER HASH
    
    Returns:
    - 1: pass (valid header and hash)
    - 2: fail (invalid header or hash)
    """
    try:
        message_parts = sms.sms_message.strip().split()
        
        # Basic format validation - expect at least 3 parts (header, mobile, hash)
        if len(message_parts) < 3:
            return 2  # fail - insufficient parts
        
        header = message_parts[0]
        mobile_number = message_parts[1]
        provided_hash = message_parts[2]
        
        # Header validation - should be alphanumeric and reasonable length
        if not re.match(r'^[A-Za-z0-9]{2,10}$', header):
            return 2  # fail - invalid header format
        
        # Mobile number basic format validation
        if not re.match(r'^\d{10,15}$', mobile_number):
            return 2  # fail - invalid mobile number format
        
        # Hash validation
        # Get salt from onboarding_mobile table
        async with pool.acquire() as conn:
            salt_result = await conn.fetchrow(
                "SELECT salt FROM onboarding_mobile WHERE mobile_number = $1 AND is_active = true",
                mobile_number
            )
        
        if not salt_result:
            return 2  # fail - mobile number not found in onboarding table
        
        salt = salt_result['salt']
        
        # Generate expected hash using header + mobile + salt
        data_to_hash = f"{header}{mobile_number}{salt}"
        expected_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
        
        # Compare provided hash with expected hash
        if provided_hash.lower() != expected_hash.lower():
            return 2  # fail - hash mismatch
        
        return 1  # pass - all validations successful
        
    except Exception as e:
        # Log error and fail safely
        print(f"Error in header_hash_check: {e}")
        return 2  # fail on error
