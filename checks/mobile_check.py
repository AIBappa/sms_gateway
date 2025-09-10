import re

async def validate_mobile_check(sms, pool):
    """
    Validates that the mobile number in SMS message exists in onboarding_mobile table.
    Expected SMS format: HEADER MOBILE_NUMBER HASH
    
    Returns:
    - 1: pass (mobile number found in onboarding table)
    - 2: fail (mobile number not found or invalid format)
    """
    try:
        message_parts = sms.sms_message.strip().split()
        
        # Extract mobile number from second part of message
        if len(message_parts) < 2:
            return 2  # fail - insufficient parts
        
        mobile_number = message_parts[1]
        
        # Basic mobile number format validation
        if not re.match(r'^\d{10,15}$', mobile_number):
            return 2  # fail - invalid mobile number format
        
        # Check if mobile number exists in onboarding_mobile table and is active
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM onboarding_mobile WHERE mobile_number = $1 AND is_active = true)",
                mobile_number
            )
        
        if exists:
            return 1  # pass
        else:
            return 2  # fail - mobile number not found in onboarding table
            
    except Exception as e:
        # Log error and fail safely
        print(f"Error in mobile_check: {e}")
        return 2  # fail on error