// Cutting a document into overlapping windows of words, so a fact that straddles a boundary is
// still whole in one chunk.

export const CHUNK_WORDS = 20;
export const OVERLAP_WORDS = 5;
export const MAX_CHUNKS = 8;

const STEP = CHUNK_WORDS - OVERLAP_WORDS;

export function wordsOf(text: string): string[] {
  return text.split(/\s+/).filter((word) => word !== "");
}

// Windows of CHUNK_WORDS words, each starting STEP words after the one before, until one reaches
// the last word. Each chunk's words are joined by one space. `words` holds at least one word.
export function chunksOf(words: string[]): string[] {
  const chunks: string[] = [];
  for (let start = 0; ; start += STEP) {
    chunks.push(words.slice(start, start + CHUNK_WORDS).join(" "));
    if (start + CHUNK_WORDS >= words.length) {
      return chunks;
    }
  }
}

// How many chunks `words` cut into, without cutting them.
export function chunkCount(words: string[]): number {
  return words.length <= CHUNK_WORDS ? 1 : Math.ceil((words.length - CHUNK_WORDS) / STEP) + 1;
}
