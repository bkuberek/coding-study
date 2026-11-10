-- Up Migration
-- The tracker as it stands, and the problem's: leave this file as it is and add your own
-- migrations after it. Migrations run as `tracker_owner`, which owns every table; your app
-- connects as `tracker_app`, which owns none and cannot bypass row-level security. Grading loads
-- another organization into these tables before your migrations run.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tracker_app') THEN
        CREATE ROLE tracker_app LOGIN PASSWORD 'tracker_app' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

CREATE TABLE tenants (
    id text PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE users (
    id text PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants (id),
    name text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'member'))
);

-- Read before the organization is known, by the key alone, so it says whose key it is.
CREATE TABLE api_keys (
    key text PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants (id),
    user_id text NOT NULL REFERENCES users (id)
);

CREATE TABLE projects (
    id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id text NOT NULL REFERENCES tenants (id),
    name text NOT NULL,
    UNIQUE (id, tenant_id)
);

-- A task's project is in the task's organization: the key names both.
CREATE TABLE tasks (
    id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id text NOT NULL REFERENCES tenants (id),
    project_id text NOT NULL,
    title text NOT NULL,
    done boolean NOT NULL DEFAULT false,
    UNIQUE (id, tenant_id),
    FOREIGN KEY (project_id, tenant_id) REFERENCES projects (id, tenant_id) ON DELETE CASCADE
);

GRANT SELECT, INSERT, UPDATE, DELETE ON tenants, users, api_keys, projects, tasks TO tracker_app;
-- Every table a later migration creates is granted the same way, so a new table is as open to
-- the app as these are until a policy closes it.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tracker_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO tracker_app;

INSERT INTO tenants (id, name) VALUES
    ('alder', 'Alder Studio'),
    ('birch', 'Birch Works');

INSERT INTO users (id, tenant_id, name, role) VALUES
    ('u-ada', 'alder', 'Ada', 'admin'),
    ('u-ari', 'alder', 'Ari', 'member'),
    ('u-bea', 'birch', 'Bea', 'admin'),
    ('u-ben', 'birch', 'Ben', 'member');

INSERT INTO api_keys (key, tenant_id, user_id) VALUES
    ('key-ada', 'alder', 'u-ada'),
    ('key-ari', 'alder', 'u-ari'),
    ('key-bea', 'birch', 'u-bea'),
    ('key-ben', 'birch', 'u-ben');

INSERT INTO projects (id, tenant_id, name) VALUES
    ('p-1', 'alder', 'Spring launch'),
    ('p-2', 'alder', 'Office move'),
    ('p-3', 'birch', 'Spring catalog');

INSERT INTO tasks (id, tenant_id, project_id, title, done) VALUES
    ('t-1', 'alder', 'p-1', 'Write the launch email', false),
    ('t-2', 'alder', 'p-1', 'Book the launch venue', true),
    ('t-3', 'alder', 'p-2', 'Order standing desks', false),
    ('t-4', 'birch', 'p-3', 'Shoot the launch photos', false),
    ('t-5', 'birch', 'p-3', 'Price the spring range', false);
