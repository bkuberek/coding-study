-- Up Migration
-- Comments on tasks, closed from the start: the policy is in the same migration as the table, so
-- there is no moment when the app can read another organization's comments. The baseline's
-- default privileges already grant the table to `tracker_app`, which is why the policy matters.
-- The task key names the organization too, so a comment cannot point at another organization's
-- task, which a plain foreign key would allow, since key checks do not see policies.

CREATE TABLE comments (
    id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id text NOT NULL REFERENCES tenants (id),
    task_id text NOT NULL,
    author_id text NOT NULL REFERENCES users (id),
    body text NOT NULL,
    FOREIGN KEY (task_id, tenant_id) REFERENCES tasks (id, tenant_id) ON DELETE CASCADE
);

CREATE INDEX comments_task ON comments (task_id);

ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON comments
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
