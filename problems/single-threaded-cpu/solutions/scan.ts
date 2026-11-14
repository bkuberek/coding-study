export function getOrder(tasks: number[][]): number[] {
  const remaining = tasks.map((_, index) => index); // unprocessed task indexes, ascending
  let time = 0;
  const order: number[] = [];
  while (remaining.length > 0) {
    // Scan every waiting task; a strict < keeps the smaller index on equal times.
    let best = -1;
    let nextArrival = Infinity;
    for (let position = 0; position < remaining.length; position++) {
      const [enqueue, processing] = tasks[remaining[position]];
      if (enqueue > time) {
        nextArrival = Math.min(nextArrival, enqueue);
      } else if (best < 0 || processing < tasks[remaining[best]][1]) {
        best = position;
      }
    }
    if (best < 0) {
      time = nextArrival; // idle until the next arrival
      continue;
    }
    const [index] = remaining.splice(best, 1);
    time += tasks[index][1];
    order.push(index);
  }
  return order;
}
