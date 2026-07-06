-- Add retirement planning fields to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_age INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS annual_contribution DECIMAL(12,2) DEFAULT 10000;
