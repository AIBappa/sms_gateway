from datetime import datetime, timezone
import re

async def validate_time_window_check(sms, pool):
    """
    Validates time window between onboarding mobile request and SMS received time.
    Compares request_timestamp in onboarding_mobile table vs received_timestamp in input_sms.
    Uses sender_number to find the onboarding record.
    
    Returns:
    - 1: pass (within time window)
    - 2: fail (outside time window or mobile not found)
    """
    try:
        sender_number = sms.sender_number.strip()
        
        # Remove any country code or special characters to get clean mobile number
        clean_mobile = re.sub(r'^[^\d]*', '', sender_number)
        
        # Basic mobile number format validation
        if not re.match(r'^\d{10,15}$', clean_mobile):
            return 2  # fail - invalid mobile number format
        
        async with pool.acquire() as conn:
            # Get validation time window from settings
            window_seconds = int(await conn.fetchval(
                "SELECT setting_value FROM system_settings WHERE setting_key = 'validation_time_window'"
            ))
            
            # Get onboarding request timestamp for this mobile number
            onboarding_result = await conn.fetchrow(
                "SELECT request_timestamp FROM onboarding_mobile WHERE mobile_number = $1 AND is_active = true",
                clean_mobile
            )
        
        if not onboarding_result:
            return 2  # fail - mobile number not found in onboarding table
        
        onboarding_timestamp = onboarding_result['request_timestamp']
        sms_received_timestamp = sms.received_timestamp
        
        # Calculate time difference between SMS received and onboarding request
        time_diff = (sms_received_timestamp - onboarding_timestamp).total_seconds()
        
        # Check if SMS was received within the allowed time window after onboarding
        if 0 <= time_diff <= window_seconds:
            return 1  # pass - within time window
        else:
            return 2  # fail - outside time window
            
    except Exception as e:
        # Log error and fail safely
        print(f"Error in time_window_check: {e}")
        return 2  # fail on error