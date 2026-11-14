-- Up Migration
-- One row per chunk: where it came from, the words it holds and their vector. A document is the
-- set of its chunks, so putting it again replaces them all in one transaction. No index on the
-- vectors: a scan of a few hundred rows is exact and fast, and an approximate index could miss a
-- chunk the cases expect.
CREATE TABLE chunks (
    document_id text NOT NULL,
    position integer NOT NULL,
    text text NOT NULL,
    embedding vector(9) NOT NULL,
    PRIMARY KEY (document_id, position)
);
