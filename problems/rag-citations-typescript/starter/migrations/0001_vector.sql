-- Up Migration
-- Turns on pgvector, so a column can hold a vector and SQL can compare two. Add your own tables in
-- migrations after this one: 0002_...sql and on.
CREATE EXTENSION IF NOT EXISTS vector;
