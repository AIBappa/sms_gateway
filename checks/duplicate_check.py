import redis
redis_client = redis.StrictRedis(host='localhost', port=6379, password=None, db=0)

async def validate_duplicate_check(sms, pool):
    if redis_client.sismember('out_sms_numbers', sms.sender_number):
        return 2  # fail
    return 1  # pass