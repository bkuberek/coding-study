// Waiting. Everything that waits goes through `setTimeout`, looked up when it waits, so that the
// virtual clock can move it.

export function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}
