-- ============================================================================
-- Subscription Killer - PostgreSQL Database Schema for pgAdmin 4
-- Hackbios 2026
-- Zero-Trust Architecture: Strictly Tracked by Transaction ID (No Bank Details)
-- ============================================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL DEFAULT 'Demo User',
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Subscriptions Table
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    transaction_ref VARCHAR(100) NOT NULL,
    merchant VARCHAR(255) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK(amount >= 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    billing_frequency VARCHAR(50) NOT NULL DEFAULT 'monthly',
    plan_name VARCHAR(100) NOT NULL DEFAULT 'Standard',
    renewal_date VARCHAR(50),
    cancellation_deadline VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_merchant_txn UNIQUE(user_id, merchant, transaction_ref)
);

-- 3. Cancellation Requests & Audit Receipts Table
CREATE TABLE IF NOT EXISTS cancellation_requests (
    request_id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    transaction_ref VARCHAR(100),
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'cancelled',
    confirmation_ref VARCHAR(100),
    message TEXT
);

-- 4. Notification Preferences Table
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    in_app_enabled INTEGER NOT NULL DEFAULT 1,
    audio_alerts INTEGER NOT NULL DEFAULT 1,
    price_alerts INTEGER NOT NULL DEFAULT 1,
    reminder_days VARCHAR(100) NOT NULL DEFAULT '7,3,1',
    preferred_channels VARCHAR(100) NOT NULL DEFAULT 'in_app,audio'
);

-- 5. Notifications & Alerts Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    transaction_ref VARCHAR(100),
    title VARCHAR(255) NOT NULL DEFAULT 'Subscription Alert',
    event_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    scheduled_at VARCHAR(100) NOT NULL,
    sent_at VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Credit Score Ledger Table (Gamified Financial Responsibility)
CREATE TABLE IF NOT EXISTS score_ledger (
    ledger_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(subscription_id) ON DELETE SET NULL,
    transaction_ref VARCHAR(100),
    action_type VARCHAR(100) NOT NULL,
    points INTEGER NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for High Performance Querying in pgAdmin 4
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_subs_user_status ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_subs_txn_ref ON subscriptions(transaction_ref);
CREATE INDEX IF NOT EXISTS idx_notifs_user_sched ON notifications(user_id, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_ledger_user_pts ON score_ledger(user_id, points);

-- ============================================================================
-- Handy Analytics Views for pgAdmin 4 Dashboard
-- ============================================================================

-- View 1: Active Subscriptions with Annual Projections
CREATE OR REPLACE VIEW vw_active_subscriptions AS
SELECT 
    subscription_id,
    user_id,
    merchant,
    plan_name,
    transaction_ref,
    amount,
    billing_frequency,
    CASE 
        WHEN billing_frequency IN ('yearly', 'annual') THEN amount
        WHEN billing_frequency = 'weekly' THEN amount * 52
        ELSE amount * 12
    END AS annual_cost_projected,
    renewal_date,
    cancellation_deadline,
    status
FROM subscriptions
WHERE status = 'active'
ORDER BY annual_cost_projected DESC;

-- View 2: Cancellation Audit Trail & Money Saved
CREATE OR REPLACE VIEW vw_cancellation_audit_ledger AS
SELECT 
    cr.request_id,
    cr.requested_at,
    s.merchant,
    cr.transaction_ref,
    s.plan_name,
    s.amount AS monthly_saved,
    cr.confirmation_ref,
    cr.status,
    cr.message
FROM cancellation_requests cr
JOIN subscriptions s ON cr.subscription_id = s.subscription_id
ORDER BY cr.requested_at DESC;

-- View 3: User Credit Score Summary & Rating Tier
CREATE OR REPLACE VIEW vw_user_credit_summary AS
SELECT 
    u.user_id,
    u.display_name,
    COALESCE(SUM(sl.points), 0) + 300 AS credit_score,
    CASE 
        WHEN COALESCE(SUM(sl.points), 0) + 300 >= 800 THEN 'Excellent (Financial Master)'
        WHEN COALESCE(SUM(sl.points), 0) + 300 >= 740 THEN 'Very Good (Defender)'
        WHEN COALESCE(SUM(sl.points), 0) + 300 >= 670 THEN 'Good (Cautious Saver)'
        WHEN COALESCE(SUM(sl.points), 0) + 300 >= 580 THEN 'Fair (Active Builder)'
        ELSE 'Seed (Getting Started)'
    END AS rating_tier,
    COUNT(sl.ledger_id) AS total_actions_taken
FROM users u
LEFT JOIN score_ledger sl ON u.user_id = sl.user_id
GROUP BY u.user_id, u.display_name;

-- ============================================================================
-- Default Seed Data (Auto-inserted if table is empty)
-- ============================================================================
INSERT INTO users (user_id, display_name, language, timezone)
VALUES (1, 'Demo User', 'en', 'Asia/Kolkata')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO notification_preferences (user_id, in_app_enabled, audio_alerts, price_alerts, reminder_days, preferred_channels)
VALUES (1, TRUE, TRUE, TRUE, '7,3,1', 'in_app,audio')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO subscriptions (user_id, transaction_ref, merchant, amount, currency, billing_frequency, plan_name, renewal_date, cancellation_deadline, status)
VALUES 
    (1, 'TXN-NTFLX-8921', 'Netflix Premium', 649.00, 'INR', 'monthly', '4K Ultra HD', '2026-10-25', '2026-10-23', 'cancelled'),
    (1, 'TXN-OPENAI-4412', 'ChatGPT Plus', 1999.00, 'INR', 'monthly', 'Plus', '2026-10-28', '2026-10-26', 'active'),
    (1, 'TXN-SPOT-7731', 'Spotify Duo', 149.00, 'INR', 'monthly', 'Premium Duo', '2026-11-04', '2026-11-02', 'active'),
    (1, 'TXN-AMZN-2384', 'Amazon Prime', 1499.00, 'INR', 'yearly', 'Annual Prime', '2027-01-15', '2027-01-13', 'cancelled'),
    (1, 'TXN-YTBE-9102', 'YouTube Premium', 149.00, 'INR', 'monthly', 'Individual', '2026-10-21', '2026-10-19', 'active'),
    (1, 'TXN-CULT-5519', 'Cult.fit Live', 1250.00, 'INR', 'monthly', 'Live Workout', '2026-10-29', '2026-10-27', 'cancelled')
ON CONFLICT (user_id, merchant, transaction_ref) DO NOTHING;

INSERT INTO score_ledger (user_id, subscription_id, transaction_ref, action_type, points, idempotency_key, note)
VALUES 
    (1, NULL, 'TXN-GENESIS-INIT', 'baseline_onboarding', 30, 'genesis-init-1', 'Initial baseline financial credit score'),
    (1, 1, 'TXN-NTFLX-8921', 'subscription_cancelled', 50, 'cancel-seed-1', 'Direct cancellation of Netflix Premium'),
    (1, 4, 'TXN-AMZN-2384', 'subscription_cancelled', 50, 'cancel-seed-4', 'Direct cancellation of Amazon Prime')
ON CONFLICT (idempotency_key) DO NOTHING;
