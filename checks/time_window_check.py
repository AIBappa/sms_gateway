from datetime import datetime, timezone

async def validate_time_window_check(sms, pool):
    async with pool.acquire() as conn:
        window = int(await conn.fetchval("SELECT setting_value FROM system_settings WHERE setting_key = 'validation_time_window'"))
    now = datetime.now(timezone.utc)
    if (now - sms.received_timestamp).total_seconds() > window:
        return 2  # fail
    return 1  # pass