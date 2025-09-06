import redis
import os

# Use the same Redis configuration as main app
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'db': 0,
}
redis_client = redis.StrictRedis(**REDIS_CONFIG)

async def validate_duplicate_check(sms, pool):
    if redis_client.sismember('out_sms_numbers', sms.sender_number):
        return 2  # fail
    return 1  # pass