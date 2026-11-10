// A file as lines, read a chunk at a time: the next chunk is asked for only when the lines of the
// last one are used up, so a file of any size takes the memory of one chunk and one line.

const CARRIAGE_RETURN = "\r";

function withoutCarriageReturn(line: string): string {
  return line.endsWith(CARRIAGE_RETURN) ? line.slice(0, -1) : line;
}

// A line break at the very end does not start another line; every other line, empty or not, is
// one. The decoder keeps a character whose bytes two chunks split, and drops a byte order mark.
export async function* linesOf(chunks: AsyncIterable<Uint8Array>): AsyncGenerator<string> {
  const decoder = new TextDecoder("utf-8");
  let rest = "";
  for await (const chunk of chunks) {
    const lines = (rest + decoder.decode(chunk, { stream: true })).split("\n");
    rest = lines.pop() ?? "";
    for (const line of lines) {
      yield withoutCarriageReturn(line);
    }
  }
  rest += decoder.decode();
  if (rest !== "") {
    yield withoutCarriageReturn(rest);
  }
}
