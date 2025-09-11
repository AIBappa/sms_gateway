import re

async def validate_mobile_check(sms, pool):
    """
    Validates that the sender mobile number exists in onboarding_mobile table.
    Expected SMS format: ONBOARD:<hash>
    Validation is based on the sender_number, not message content.
    
    Returns:
    - 1: pass (sender mobile number found in onboarding table)
    - 2: fail (sender mobile number not found or invalid)
    """
    try:
        sender_number = sms.sender_number.strip()
        
        # Remove any country code or special characters to get clean mobile number
        clean_mobile = re.sub(r'^[^\d]*', '', sender_number)
        
        # Basic mobile number format validation
        if not re.match(r'^\d{10,15}$', clean_mobile):
            return 2  # fail - invalid mobile number format
        
        # Check if sender mobile number exists in onboarding_mobile table and is active
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM onboarding_mobile WHERE mobile_number = $1 AND is_active = true)",
                clean_mobile
            )
        
        if exists:
            return 1  # pass
        else:
            return 2  # fail - sender mobile number not found in onboarding table
            
    except Exception as e:
        # Log error and fail safely
        print(f"Error in mobile_check: {e}")
        return 2  # fail on error