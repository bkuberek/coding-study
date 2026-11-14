// The chunks in Postgres: replacing a document's, listing them, and finding the nearest to a vector.

import { pool } from "./db.ts";

export type StoredChunk = { position: number; text: string };
export type Hit = { documentId: string; position: number; text: string; score: number };

// Replaces every chunk of `documentId` in one transaction, so a reader sees the old version or the
// new one, never a mix, and no chunk of the old version is left behind.
export async function replaceChunks(
  documentId: string,
  texts: string[],
  vectors: number[][],
): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("DELETE FROM chunks WHERE document_id = $1", [documentId]);
    await client.query(
      `INSERT INTO chunks (document_id, position, text, embedding)
       SELECT $1, ordinality - 1, text, embedding::vector
         FROM unnest($2::text[], $3::text[]) WITH ORDINALITY AS given (text, embedding, ordinality)`,
      [documentId, texts, vectors.map((vector) => JSON.stringify(vector))],
    );
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function chunksOfDocument(documentId: string): Promise<StoredChunk[]> {
  const found = await pool.query<StoredChunk>(
    "SELECT position, text FROM chunks WHERE document_id = $1 ORDER BY position",
    [documentId],
  );
  return found.rows;
}

// The `k` chunks most like `vector` by cosine similarity, each scoring at least `minScore`. `<=>`
// is pgvector's cosine distance, one minus the similarity. Equal scores go by document id, compared
// by code point rather than by the database's collation, then by position.
export async function nearest(vector: number[], k: number, minScore: number): Promise<Hit[]> {
  const found = await pool.query<{ document_id: string; position: number; text: string; score: number }>(
    `SELECT document_id, position, text, 1 - (embedding <=> $1::vector) AS score
       FROM chunks
      WHERE 1 - (embedding <=> $1::vector) >= $2
      ORDER BY embedding <=> $1::vector, document_id COLLATE "C", position
      LIMIT $3`,
    [JSON.stringify(vector), minScore, k],
  );
  return found.rows.map((row) => ({
    documentId: row.document_id,
    position: row.position,
    text: row.text,
    score: row.score,
  }));
}
