-- Ensure pgvector is available at first boot
CREATE EXTENSION IF NOT EXISTS vector;
-- n8n needs its own schema
CREATE SCHEMA IF NOT EXISTS n8n;
