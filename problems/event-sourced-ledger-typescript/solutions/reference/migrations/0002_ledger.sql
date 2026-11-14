-- Up Migration
-- The store's rules, kept by the database. One event per version of a stream: of two appends at
-- the same version, the second fails, which is what optimistic concurrency needs. One event per
-- event id in a stream: a replayed command fails the same way and is answered as a replay. The two
-- events of a transfer share their id, one in each stream.
CREATE UNIQUE INDEX events_by_stream_version ON events (stream_id, version);
CREATE UNIQUE INDEX events_by_stream_event_id ON events (stream_id, event_id);

-- Append-only: an event, once written, is never changed or removed.
CREATE FUNCTION refuse_event_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'events are append-only';
END;
$$;

CREATE TRIGGER events_append_only BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION refuse_event_change();

-- The balance projection: one row per account, as the events so far leave it. The service fills
-- it from the store when it starts, and each append moves it along in the same transaction.
CREATE TABLE accounts (
    account text PRIMARY KEY,
    balance bigint NOT NULL CHECK (balance >= 0),
    version integer NOT NULL CHECK (version > 0)
);
