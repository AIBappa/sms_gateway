from datetime import datetime, timezone

async def validate_time_window_check(sms, pool):
    window = int(await pool.fetchval("SELECT setting_value FROM system_settings WHERE setting_key = 'validation_time_window'"))
    now = datetime.now(timezone.utc)
    if (now - sms.received_timestamp).seconds > window:
        return 2  # fail
    return 1  # pass