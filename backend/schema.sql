CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    worker_id UUID,
    job_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attmepts INTEGER NOT NULL DEFAULT 3,
    result JSONB,
    last_error TEXT,
    lease_expires_at TIMESTAMPTZ,
    idemptency_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS job_attempts (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id),
    attempt_number INTEGER DEFAULT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT DEFAULT NULL,
    UNIQUE (job_id, attempt_number)
);
