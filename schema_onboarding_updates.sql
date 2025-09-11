-- Database schema updates for onboarding functionality
-- Add onboarding_mobile table as specified in update_prompt1.md

-- 7. onboarding_mobile table for mobile number validation
CREATE TABLE IF NOT EXISTS onboarding_mobile (
    mobile_number VARCHAR(15) PRIMARY KEY,
    hash VARCHAR(64) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    request_timestamp TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for onboarding_mobile
CREATE INDEX IF NOT EXISTS idx_onboarding_hash ON onboarding_mobile (hash);
CREATE INDEX IF NOT EXISTS idx_onboarding_request_timestamp ON onboarding_mobile (request_timestamp);
CREATE INDEX IF NOT EXISTS idx_onboarding_is_active ON onboarding_mobile (is_active);

-- Add new system settings for onboarding functionality
INSERT INTO system_settings (setting_key, setting_value) 
SELECT setting_key, setting_value FROM (VALUES
    ('allowed_country_codes', '["91", "1", "44", "61", "33", "49"]'),
    ('hash_salt_length', '16'),
    ('onboarding_expiry_hours', '24'),
    ('foreign_number_validation', 'true')
) AS new_settings(setting_key, setting_value)
WHERE NOT EXISTS (
    SELECT 1 FROM system_settings WHERE system_settings.setting_key = new_settings.setting_key
);

-- Update sms_monitor table to include new foreign_number_check column
ALTER TABLE sms_monitor ADD COLUMN IF NOT EXISTS foreign_number_check INTEGER DEFAULT 0;

-- Update check_sequence and check_enabled settings to include new foreign_number check
UPDATE system_settings 
SET setting_value = '["blacklist", "duplicate", "foreign_number", "header_hash", "mobile", "time_window"]'
WHERE setting_key = 'check_sequence';

UPDATE system_settings 
SET setting_value = '{"blacklist":true, "duplicate":true, "foreign_number":true, "header_hash":true, "mobile":true, "time_window":true}'
WHERE setting_key = 'check_enabled';
