-- PostgreSQL schema for Astrafenix AI reporting system

-- Team members (developers) table
CREATE TABLE IF NOT EXISTS team_members (
    developer_id VARCHAR(100) PRIMARY KEY,
    developer_name VARCHAR(150) NOT NULL,
    team_id VARCHAR(50),
    role_in_team VARCHAR(50) DEFAULT 'developer',
    email VARCHAR(255) UNIQUE,
    skills JSONB,
    join_date DATE DEFAULT CURRENT_DATE
);

-- Create indexes separately AFTER creating the table
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);

-- Developer daily reports
CREATE TABLE IF NOT EXISTS developer_reports (
    report_id SERIAL PRIMARY KEY,
    developer_id VARCHAR(100) NOT NULL,
    developer_name VARCHAR(150) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    raw_responses JSONB,
    structured_report JSONB,
    summary TEXT,
    progress_percentage INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    team_lead_notes TEXT,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(developer_id, date),
    FOREIGN KEY (developer_id) REFERENCES team_members(developer_id) ON DELETE CASCADE
);

-- Create indexes for developer_reports
CREATE INDEX IF NOT EXISTS idx_developer_reports_date ON developer_reports(date);
CREATE INDEX IF NOT EXISTS idx_developer_reports_status ON developer_reports(status);
CREATE INDEX IF NOT EXISTS idx_developer_reports_developer_date_status ON developer_reports(developer_id, date, status);

-- Team daily summary
CREATE TABLE IF NOT EXISTS team_daily_summary (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR(50) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    total_developers INTEGER DEFAULT 0,
    reports_submitted INTEGER DEFAULT 0,
    overall_progress DECIMAL(5,2) DEFAULT 0.0,
    blockers_count INTEGER DEFAULT 0,
    summary_report TEXT,
    action_items JSONB DEFAULT '[]',
    risk_level VARCHAR(20) DEFAULT 'low',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, date)
);

-- Create index for team_daily_summary
CREATE INDEX IF NOT EXISTS idx_team_daily_summary_date ON team_daily_summary(date);
CREATE INDEX IF NOT EXISTS idx_team_daily_summary_team_date ON team_daily_summary(team_id, date);