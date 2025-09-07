import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict
import asyncpg
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import requests

# Pydantic models
class SMSInput(BaseModel):
    sender_number: str
    sms_message: str
    received_timestamp: datetime

class BatchSMSData(BaseModel):
    uuid: str
    sender_number: str
    sms_message: str
    received_timestamp: datetime

# Load configuration
CONFIG_FILE = os.path.expanduser('~/sms_bridge_config.json')
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}

CF_BACKEND_URL = os.getenv('CF_BACKEND_URL', config.get('cf_endpoint', 'https://default-url-if-not-set'))
API_KEY = os.getenv('CF_API_KEY', config.get('cf_api_key', ''))

HASH_SECRET_KEY = os.getenv('HASH_SECRET_KEY', '')  # Added for hash validation

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'database': os.getenv('POSTGRES_DB', 'sms_bridge'),
    'user': os.getenv('POSTGRES_USER', 'sms_user'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'port': int(os.getenv('POSTGRES_PORT', 6432)),  # pgbouncer port
}

REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'db': 0,
}

app = FastAPI()
redis_client = redis.StrictRedis(**REDIS_CONFIG)
pool = None

# Logging setup with file handlers for persistent logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_DIR = os.getenv('LOG_DIR', '/app/logs')

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging with both file and console handlers
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Console output for Docker logs
    ]
)

# Add rotating file handlers for persistent logging
from logging.handlers import RotatingFileHandler

# Create rotating file handler for general logs
rotating_handler = RotatingFileHandler(
    f'{LOG_DIR}/sms_server.log',
    maxBytes=50*1024*1024,  # 50MB
    backupCount=5
)
rotating_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create rotating file handler for errors
error_handler = RotatingFileHandler(
    f'{LOG_DIR}/sms_server_errors.log',
    maxBytes=50*1024*1024,  # 50MB
    backupCount=5
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Add handlers to root logger
logging.getLogger().addHandler(rotating_handler)
logging.getLogger().addHandler(error_handler)

logger = logging.getLogger(__name__)
logger.info(f"SMS Server starting with log level: {LOG_LEVEL}")
logger.info(f"Logs will be written to: {LOG_DIR}")

async def get_db_pool():
    global pool
    if pool is None:
        # Disable statement cache for PgBouncer compatibility
        pool = await asyncpg.create_pool(**POSTGRES_CONFIG, min_size=1, max_size=10, statement_cache_size=0)
    return pool

async def get_setting(key: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT setting_value FROM system_settings WHERE setting_key = $1", key)
        if result is None:
            return None
        # Try to parse as JSON, if it fails return as string
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result

async def run_validation_checks(batch_sms_data: List[BatchSMSData]):
    check_sequence = await get_setting('check_sequence')
    check_enabled = await get_setting('check_enabled')
    pool = await get_db_pool()
    
    for sms in batch_sms_data:
        # Initialize all check results to 0 (not run)
        results = {
            'blacklist_check': 0,
            'duplicate_check': 0,
            'header_check': 0,
            'hash_length_check': 0,
            'mobile_check': 0,
            'time_window_check': 0
        }
        overall_status = 'valid'
        failed_check = None
        
        for check_name in check_sequence:
            if not check_enabled.get(check_name, False):
                results[f'{check_name}_check'] = 3  # skipped
                continue
            
            # Use explicit function mapping instead of globals() to prevent code injection
            if check_name not in VALIDATION_FUNCTIONS:
                logger.error(f"Unknown validation check: {check_name}")
                results[f'{check_name}_check'] = 2  # fail
                overall_status = 'invalid'
                failed_check = check_name
                break
            
            check_func = VALIDATION_FUNCTIONS[check_name]
            result = await check_func(sms, pool)
            results[f'{check_name}_check'] = result
            
            if result == 2:  # fail
                overall_status = 'invalid'
                failed_check = check_name
                break
            elif result == 3:  # skipped
                continue
        
        # Update sms_monitor
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sms_monitor (uuid, overall_status, failed_at_check, processing_completed_at, 
                                         blacklist_check, duplicate_check, header_check, hash_length_check, 
                                         mobile_check, time_window_check)
                VALUES ($1, $2, $3, NOW(), $4, $5, $6, $7, $8, $9)
                ON CONFLICT (uuid) DO UPDATE SET 
                    overall_status = EXCLUDED.overall_status,
                    failed_at_check = EXCLUDED.failed_at_check,
                    processing_completed_at = EXCLUDED.processing_completed_at,
                    blacklist_check = EXCLUDED.blacklist_check,
                    duplicate_check = EXCLUDED.duplicate_check,
                    header_check = EXCLUDED.header_check,
                    hash_length_check = EXCLUDED.hash_length_check,
                    mobile_check = EXCLUDED.mobile_check,
                    time_window_check = EXCLUDED.time_window_check
            """, sms.uuid, overall_status, failed_check, *results.values())
        
        if overall_status == 'valid':
            # Insert to out_sms and Redis
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO out_sms (uuid, sender_number, sms_message) VALUES ($1, $2, $3)
                """, sms.uuid, sms.sender_number, sms.sms_message)
            redis_client.sadd('out_sms_numbers', sms.sender_number)

async def batch_processor():
    while True:
        pool = await get_db_pool()
        batch_size = int(await get_setting('batch_size'))
        last_uuid = await get_setting('last_processed_uuid')
        
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT uuid, sender_number, sms_message, received_timestamp 
                FROM input_sms 
                WHERE uuid > $1 
                ORDER BY uuid 
                LIMIT $2
            """, last_uuid, batch_size)
        
        if rows:
            batch_data = [BatchSMSData(**dict(row)) for row in rows]
            await run_validation_checks(batch_data)
            
            # Update last_processed_uuid
            new_last_uuid = rows[-1]['uuid']
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE system_settings SET setting_value = $1 WHERE setting_key = 'last_processed_uuid'
                """, str(new_last_uuid))
        
        await asyncio.sleep(1)  # Adjust as needed

@app.on_event("startup")
async def startup_event():
    # Cache warmup
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        numbers = await conn.fetch("SELECT sender_number FROM out_sms")
        for row in numbers:
            redis_client.sadd('out_sms_numbers', row['sender_number'])
    
    # Start batch processor
    asyncio.create_task(batch_processor())

@app.post("/sms/receive")
async def receive_sms(sms_data: SMSInput, background_tasks: BackgroundTasks):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO input_sms (sender_number, sms_message, received_timestamp) 
            VALUES ($1, $2, $3)
        """, sms_data.sender_number, sms_data.sms_message, sms_data.received_timestamp)
    
    # Optionally forward to CF backend
    if CF_BACKEND_URL and API_KEY:
        try:
            response = requests.post(CF_BACKEND_URL, json=sms_data.dict(), headers={'Authorization': f'Bearer {API_KEY}'}, timeout=5)
            logger.info(f"Forwarded SMS, status: {response.status_code}")
        except Exception as e:
            logger.warning(f"Forwarding failed: {e}")
    
    return {"status": "received"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import validation functions
from checks.blacklist_check import validate_blacklist_check
from checks.duplicate_check import validate_duplicate_check
from checks.header_check import validate_header_check
from checks.hash_length_check import validate_hash_length_check
from checks.mobile_check import validate_mobile_check
from checks.time_window_check import validate_time_window_check

# Explicit function mapping dictionary to prevent code injection
VALIDATION_FUNCTIONS = {
    'blacklist': validate_blacklist_check,
    'duplicate': validate_duplicate_check,
    'header': validate_header_check,
    'hash_length': validate_hash_length_check,
    'mobile': validate_mobile_check,
    'time_window': validate_time_window_check
}
