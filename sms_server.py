import os
import json
import asyncio
import logging
import secrets
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional
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

# New models for onboarding functionality
class OnboardingRequest(BaseModel):
    mobile_number: str

class OnboardingResponse(BaseModel):
    mobile_number: str
    hash: str
    message: str

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
            'foreign_number_check': 0,
            'header_hash_check': 0,
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
                                         blacklist_check, duplicate_check, foreign_number_check, header_hash_check, 
                                         mobile_check, time_window_check)
                VALUES ($1, $2, $3, NOW(), $4, $5, $6, $7, $8, $9)
                ON CONFLICT (uuid) DO UPDATE SET 
                    overall_status = EXCLUDED.overall_status,
                    failed_at_check = EXCLUDED.failed_at_check,
                    processing_completed_at = EXCLUDED.processing_completed_at,
                    blacklist_check = EXCLUDED.blacklist_check,
                    duplicate_check = EXCLUDED.duplicate_check,
                    foreign_number_check = EXCLUDED.foreign_number_check,
                    header_hash_check = EXCLUDED.header_hash_check,
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
            
            # Forward to cloud backend only after validation passes
            if CF_BACKEND_URL and API_KEY:
                try:
                    # Convert datetime to string for JSON serialization
                    sms_dict = {
                        'sender_number': sms.sender_number,
                        'sms_message': sms.sms_message,
                        'received_timestamp': sms.received_timestamp.isoformat()
                    }
                    response = requests.post(CF_BACKEND_URL, json=sms_dict, headers={'Authorization': f'Bearer {API_KEY}'}, timeout=5)
                    logger.info(f"Forwarded validated SMS to cloud, status: {response.status_code}")
                except Exception as e:
                    logger.warning(f"Cloud forwarding failed for validated SMS: {e}")

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
            # Convert UUID objects to strings for Pydantic model
            batch_data = []
            for row in rows:
                row_dict = dict(row)
                row_dict['uuid'] = str(row_dict['uuid'])  # Convert UUID to string
                batch_data.append(BatchSMSData(**row_dict))
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
    
    return {"status": "received"}

@app.post("/onboarding/register", response_model=OnboardingResponse)
async def register_mobile(request: OnboardingRequest):
    """
    Register a mobile number for onboarding and generate hash.
    Returns the mobile number, hash, and instruction message.
    """
    try:
        pool = await get_db_pool()
        mobile_number = request.mobile_number.strip()
        
        # Validate mobile number format
        import re
        if not re.match(r'^\d{10,15}$', mobile_number):
            raise HTTPException(status_code=400, detail="Invalid mobile number format")
        
        # Generate salt
        async with pool.acquire() as conn:
            salt_length = int(await conn.fetchval(
                "SELECT setting_value FROM system_settings WHERE setting_key = 'hash_salt_length'"
            ))
        
        salt = secrets.token_hex(salt_length // 2)  # hex gives 2 chars per byte
        
        # Check if mobile number already exists and is active
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT mobile_number, is_active FROM onboarding_mobile WHERE mobile_number = $1",
                mobile_number
            )
            
            if existing and existing['is_active']:
                raise HTTPException(status_code=409, detail="Mobile number already registered and active")
            
            # Insert or update onboarding record
            if existing:
                # Reactivate existing record with new salt
                await conn.execute("""
                    UPDATE onboarding_mobile 
                    SET salt = $1, request_timestamp = NOW(), is_active = true 
                    WHERE mobile_number = $2
                """, salt, mobile_number)
            else:
                # Create new record
                await conn.execute("""
                    INSERT INTO onboarding_mobile (mobile_number, salt, hash) 
                    VALUES ($1, $2, $3)
                """, mobile_number, salt, "")  # hash will be computed below
        
        # Generate hash for onboarding (ONBOARD header + mobile + salt)
        demo_header = "ONBOARD"
        data_to_hash = f"{demo_header}{mobile_number}{salt}"
        computed_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
        
        # Update the hash in database
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE onboarding_mobile SET hash = $1 WHERE mobile_number = $2",
                computed_hash, mobile_number
            )
        
        message = f"ONBOARD:{computed_hash}"
        
        return OnboardingResponse(
            mobile_number=mobile_number,
            hash=computed_hash,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in register_mobile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/onboarding/status/{mobile_number}")
async def get_onboarding_status(mobile_number: str):
    """
    Get onboarding status for a mobile number.
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            onboarding_record = await conn.fetchrow(
                "SELECT mobile_number, request_timestamp, is_active FROM onboarding_mobile WHERE mobile_number = $1",
                mobile_number
            )
            
            if not onboarding_record:
                raise HTTPException(status_code=404, detail="Mobile number not found in onboarding system")
            
            # Check if any SMS has been successfully validated for this mobile
            sms_validated = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM input_sms i 
                    JOIN sms_monitor m ON i.uuid = m.uuid 
                    WHERE i.sms_message LIKE '%' || $1 || '%' 
                    AND m.overall_status = 'valid'
                )
            """, mobile_number)
        
        return {
            "mobile_number": onboarding_record['mobile_number'],
            "request_timestamp": onboarding_record['request_timestamp'],
            "is_active": onboarding_record['is_active'],
            "sms_validated": sms_validated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_onboarding_status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/onboarding/{mobile_number}")
async def deactivate_mobile(mobile_number: str):
    """
    Deactivate a mobile number from onboarding system.
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE onboarding_mobile SET is_active = false WHERE mobile_number = $1",
                mobile_number
            )
            
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Mobile number not found")
        
        return {"message": "Mobile number deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deactivate_mobile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import validation functions
from checks.blacklist_check import validate_blacklist_check
from checks.duplicate_check import validate_duplicate_check
from checks.foreign_number_check import validate_foreign_number_check
from checks.header_hash_check import validate_header_hash_check
from checks.mobile_check import validate_mobile_check
from checks.time_window_check import validate_time_window_check

# Explicit function mapping dictionary to prevent code injection
VALIDATION_FUNCTIONS = {
    'blacklist': validate_blacklist_check,
    'duplicate': validate_duplicate_check,
    'foreign_number': validate_foreign_number_check,
    'header_hash': validate_header_hash_check,
    'mobile': validate_mobile_check,
    'time_window': validate_time_window_check
}
