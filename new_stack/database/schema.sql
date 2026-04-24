-- PostgreSQL Schema for Fire Department Web System

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Define Enum types for strict validation
CREATE TYPE user_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE user_role AS ENUM ('ADMIN', 'COBOM', 'GB', 'SGB', 'POSTO');

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    google_id TEXT UNIQUE NOT NULL,
    status user_status NOT NULL DEFAULT 'pending',
    role user_role,
    
    -- Hierarchical Scoping
    batalhao TEXT,
    sgb TEXT,
    posto TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for performance on lookup and scoping queries
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_scope ON users(batalhao, sgb, posto);
