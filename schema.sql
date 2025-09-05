-- 1. input_sms
CREATE TABLE input_sms (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_number VARCHAR(15) NOT NULL,
    sms_message TEXT NOT NULL,
    received_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_uuid_btree (uuid),
    INDEX idx_received_timestamp (received_timestamp),
    INDEX idx_created_at (created_at)
);

-- 2. sms_monitor
CREATE TABLE sms_monitor (
    uuid UUID PRIMARY KEY REFERENCES input_sms(uuid),
    blacklist_check INTEGER DEFAULT 0,
    duplicate_check INTEGER DEFAULT 0,
    header_check INTEGER DEFAULT 0,
    hash_length_check INTEGER DEFAULT 0,
    mobile_check INTEGER DEFAULT 0,
    time_window_check INTEGER DEFAULT 0,
    overall_status VARCHAR(20) DEFAULT 'pending',
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    failed_at_check VARCHAR(20),
    batch_id UUID,
    retry_count INTEGER DEFAULT 0,
    INDEX idx_overall_status (overall_status),
    INDEX idx_batch_id (batch_id),
    INDEX idx_processing_started (processing_started_at)
);

-- 3. system_settings
CREATE TABLE system_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_settings (setting_key, setting_value) VALUES
('batch_size', '20'),
('blacklist_threshold', '10'),
('last_processed_uuid', '00000000-0000-0000-0000-000000000000'),
('check_sequence', '["blacklist", "duplicate", "header", "hash_length", "mobile", "time_window"]'),
('check_enabled', '{"blacklist":true, "duplicate":true, "header":true, "hash_length":true, "mobile":true, "time_window":true}'),
('validation_time_window', '3600'),
('out_sms_cache_ttl', '604800'),
('max_database_retries', '3'),
('log_level', 'INFO'),
('parallel_workers', '1'),
('maintenance_mode', 'false'),
('pgbouncer_pool_size', '10'),
('redis_host', 'localhost'),
('redis_port', '6379');

-- 4. out_sms
CREATE TABLE out_sms (
    uuid UUID PRIMARY KEY REFERENCES input_sms(uuid),
    sender_number VARCHAR(15) NOT NULL,
    sms_message TEXT NOT NULL,
    validation_status VARCHAR(20) DEFAULT 'valid',
    forwarded_timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_sender_number (sender_number),
    INDEX idx_forwarded_timestamp (forwarded_timestamp)
);

-- 5. blacklist_sms
CREATE TABLE blacklist_sms (
    sender_number VARCHAR(15) PRIMARY KEY,
    blacklisted_at TIMESTAMPTZ DEFAULT NOW(),
    reason VARCHAR(100) DEFAULT 'threshold_exceeded',
    message_count INTEGER DEFAULT 0
);

-- 6. count_sms
CREATE TABLE count_sms (
    sender_number VARCHAR(15) PRIMARY KEY,
    message_count INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_message_count (message_count),
    INDEX idx_last_updated (last_updated)
);