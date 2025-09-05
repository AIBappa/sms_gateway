import os
import hmac
import hashlib

async def validate_hash_length_check(sms, pool):
    key = os.getenv('HASH_SECRET_KEY', '')
    if not key:
        # If no key, fall back to basic length check
        if len(sms.sms_message) < 5:
            return 2  # fail
        return 1  # pass
    
    # Compute HMAC hash of the message
    message = sms.sms_message.encode('utf-8')
    computed_hash = hmac.new(key.encode('utf-8'), message, hashlib.sha256).hexdigest()
    
    # Validate: check message length and hash length (SHA256 hex is 64 chars)
    if len(sms.sms_message) < 5 or len(computed_hash) != 64:
        return 2  # fail
    return 1  # pass