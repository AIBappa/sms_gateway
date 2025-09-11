import os
import hmac
import hashlib
import re

async def validate_header_hash_check(sms, pool):
    """
    Combined header and hash validation check.
    Validates SMS message format: ONBOARD:<hash>
    
    Returns:
    - 1: pass (valid header and hash)
    - 2: fail (invalid header or hash)
    """
    try:
        message = sms.sms_message.strip()
        
        # Check if message starts with ONBOARD: pattern
        if not message.startswith("ONBOARD:"):
            return 2  # fail - invalid header format
        
        # Extract hash from ONBOARD:<hash> format
        try:
            provided_hash = message.split("ONBOARD:", 1)[1].strip()
        except IndexError:
            return 2  # fail - no hash after ONBOARD:
        
        # Basic hash format validation (should be 64 character hex for SHA256)
        if not re.match(r'^[a-fA-F0-9]{64}$', provided_hash):
            return 2  # fail - invalid hash format
        
        # Get the sender's mobile number and check in onboarding table
        sender_number = sms.sender_number.strip()
        
        # Remove any country code or special characters to get clean mobile number
        clean_mobile = re.sub(r'^[^\d]*', '', sender_number)
        
        # Check if mobile number exists in onboarding table and get stored hash
        async with pool.acquire() as conn:
            onboarding_result = await conn.fetchrow(
                "SELECT hash FROM onboarding_mobile WHERE mobile_number = $1 AND is_active = true",
                clean_mobile
            )
        
        if not onboarding_result:
            return 2  # fail - mobile number not found in onboarding table
        
        stored_hash = onboarding_result['hash']
        
        # Compare provided hash with stored hash
        if provided_hash.lower() != stored_hash.lower():
            return 2  # fail - hash mismatch
        
        return 1  # pass - all validations successful
        
    except Exception as e:
        # Log error and fail safely
        print(f"Error in header_hash_check: {e}")
        return 2  # fail on error
