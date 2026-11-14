const SENTENCE_ENDINGS = new Set([".", "!", "?"]);
const NO_SENTENCE_END = -1;

function tokenSpans(text: string): number[][] {
  const spans: number[][] = [];
  const token = /[^ \t\n\r]+/g;
  for (let match = token.exec(text); match !== null; match = token.exec(text)) {
    spans.push([match.index, match.index + match[0].length]);
  }
  return spans;
}

// For each token, the index of the last token at or before it that ends a sentence.
function lastSentenceEndByToken(text: string, spans: number[][]): number[] {
  let latest = NO_SENTENCE_END;
  return spans.map(([, end], index) => {
    if (SENTENCE_ENDINGS.has(text[end - 1])) {
      latest = index;
    }
    return latest;
  });
}

export function chunkText(text: string, maxTokens: number, overlap: number): number[][] {
  if (overlap >= maxTokens) {
    return [];
  }
  const spans = tokenSpans(text);
  const lastSentenceEnd = lastSentenceEndByToken(text, spans);
  const final = spans.length - 1;
  const chunks: number[][] = [];
  let first = 0;
  let last = -1;
  // The loop stops once a chunk reaches the final token, so the shared tail of the last chunk
  // never becomes a chunk of its own.
  while (last < final) {
    const windowLast = first + maxTokens - 1;
    if (windowLast >= final) {
      last = final;
    } else if (lastSentenceEnd[windowLast] >= first + overlap) {
      last = lastSentenceEnd[windowLast];
    } else {
      last = windowLast;
    }
    chunks.push([spans[first][0], spans[last][1]]);
    first = last - overlap + 1;
  }
  return chunks;
}
