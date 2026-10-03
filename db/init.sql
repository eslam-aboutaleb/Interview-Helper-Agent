-- Initialize database for Interview Helper Agent
-- This schema mirrors the SQLAlchemy models in backend/models.py.
-- The application also runs Base.metadata.create_all() on startup, so
-- this file is primarily for explicit provisioning. Keep both in sync.

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT check_email_length CHECK (LENGTH(email) <= 255),
    CONSTRAINT check_user_role CHECK (role IN ('user', 'admin'))
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- User sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON user_sessions (token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions (expires_at);

-- Questions
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
    job_title VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    difficulty INTEGER NOT NULL DEFAULT 1,
    is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    tags VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT check_job_title_length CHECK (LENGTH(job_title) >= 2 AND LENGTH(job_title) <= 100),
    CONSTRAINT check_question_text_length CHECK (LENGTH(question_text) >= 10 AND LENGTH(question_text) <= 2000),
    CONSTRAINT check_question_type CHECK (question_type IN ('technical', 'behavioral', 'mixed')),
    CONSTRAINT check_difficulty_range CHECK (difficulty >= 1 AND difficulty <= 5)
);
CREATE INDEX IF NOT EXISTS idx_job_title_type ON questions (job_title, question_type);
CREATE INDEX IF NOT EXISTS idx_is_flagged ON questions (is_flagged);
CREATE INDEX IF NOT EXISTS idx_created_at ON questions (created_at);
CREATE INDEX IF NOT EXISTS idx_questions_user_id ON questions (user_id);

-- Question sets
CREATE TABLE IF NOT EXISTS question_sets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    job_title VARCHAR(100) NOT NULL,
    question_ids TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT check_set_name_length CHECK (LENGTH(name) >= 1 AND LENGTH(name) <= 200),
    CONSTRAINT check_set_job_title_length CHECK (LENGTH(job_title) >= 2 AND LENGTH(job_title) <= 100)
);
CREATE INDEX IF NOT EXISTS idx_set_job_title ON question_sets (job_title);
CREATE INDEX IF NOT EXISTS idx_set_created_at ON question_sets (created_at);

-- User ratings
CREATE TABLE IF NOT EXISTS user_ratings (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    rating DOUBLE PRECISION NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT check_question_id_positive CHECK (question_id > 0),
    CONSTRAINT check_rating_range CHECK (rating >= 1.0 AND rating <= 5.0)
);
CREATE INDEX IF NOT EXISTS idx_rating_question_id ON user_ratings (question_id);
CREATE INDEX IF NOT EXISTS idx_rating_created_at ON user_ratings (created_at);

-- Question history (tracks user interactions with questions)
CREATE TABLE IF NOT EXISTS question_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
    question_id INTEGER,
    action VARCHAR(50) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT check_history_action CHECK (action IN ('generated', 'viewed', 'rated', 'flagged', 'created', 'deleted'))
);
CREATE INDEX IF NOT EXISTS idx_history_user_id ON question_history (user_id);
CREATE INDEX IF NOT EXISTS idx_history_question_id ON question_history (question_id);
CREATE INDEX IF NOT EXISTS idx_history_action ON question_history (action);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON question_history (created_at);

-- User documents (resumes and job descriptions)
CREATE TABLE IF NOT EXISTS user_documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    document_type VARCHAR(20) NOT NULL,
    filename VARCHAR(255),
    content_text TEXT NOT NULL,
    parsed_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT check_document_type CHECK (document_type IN ('resume', 'jd'))
);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON user_documents (user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON user_documents (document_type);

-- Interview sessions
CREATE TABLE IF NOT EXISTS interview_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    job_title VARCHAR(100) NOT NULL,
    session_type VARCHAR(20) NOT NULL DEFAULT 'mixed',
    difficulty INTEGER NOT NULL DEFAULT 3,
    target_difficulty INTEGER NOT NULL DEFAULT 3,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    current_turn INTEGER NOT NULL DEFAULT 0,
    max_turns INTEGER NOT NULL DEFAULT 7,
    document_id INTEGER REFERENCES user_documents (id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT check_session_type CHECK (session_type IN ('technical', 'behavioral', 'mixed')),
    CONSTRAINT check_session_difficulty CHECK (difficulty >= 1 AND difficulty <= 5),
    CONSTRAINT check_session_status CHECK (status IN ('active', 'completed'))
);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_status ON interview_sessions (status);

-- Interview messages
CREATE TABLE IF NOT EXISTS interview_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES interview_sessions (id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    question_id INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT check_message_role CHECK (role IN ('interviewer', 'candidate', 'system'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON interview_messages (session_id);

-- Answer evaluations
CREATE TABLE IF NOT EXISTS answer_evaluations (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES interview_sessions (id) ON DELETE CASCADE,
    message_id INTEGER,
    question_id INTEGER,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    overall_score DOUBLE PRECISION NOT NULL,
    technical_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    communication_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    completeness_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    feedback JSONB,
    model_answer TEXT,
    next_action VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT check_overall_score_range CHECK (overall_score >= 0 AND overall_score <= 10)
);
CREATE INDEX IF NOT EXISTS idx_evaluations_session_id ON answer_evaluations (session_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_user_id ON answer_evaluations (user_id);
