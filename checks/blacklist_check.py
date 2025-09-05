async def validate_blacklist_check(sms, pool):
    threshold = int(await pool.fetchval("SELECT setting_value FROM system_settings WHERE setting_key = 'blacklist_threshold'"))
    async with pool.acquire() as conn:
        count = await conn.fetchval("""
            INSERT INTO count_sms (sender_number, message_count) VALUES ($1, 1)
            ON CONFLICT (sender_number) DO UPDATE SET message_count = count_sms.message_count + 1 RETURNING message_count
        """, sms.sender_number)
        if count > threshold:
            await conn.execute("INSERT INTO blacklist_sms (sender_number) VALUES ($1) ON CONFLICT DO NOTHING", sms.sender_number)
            return 2  # fail
    return 1  # pass