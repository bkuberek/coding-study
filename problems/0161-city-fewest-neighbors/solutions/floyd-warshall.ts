export function findTheCity(n: number, edges: number[][], distanceThreshold: number): number {
  const dist = Array.from({ length: n }, (_, i) => {
    const row = new Array<number>(n).fill(Infinity);
    row[i] = 0;
    return row;
  });
  for (const [a, b, w] of edges) {
    dist[a][b] = w;
    dist[b][a] = w;
  }
  // After step m, dist[i][j] is the shortest route that only passes through cities 0..m.
  for (let middle = 0; middle < n; middle++) {
    const through = dist[middle];
    for (let i = 0; i < n; i++) {
      const toMiddle = dist[i][middle];
      if (toMiddle === Infinity) continue;
      const row = dist[i];
      for (let j = 0; j < n; j++) {
        if (toMiddle + through[j] < row[j]) row[j] = toMiddle + through[j];
      }
    }
  }
  let bestCity = -1;
  let bestCount = n + 1;
  for (let city = 0; city < n; city++) {
    let count = 0;
    for (let other = 0; other < n; other++) {
      if (other !== city && dist[city][other] <= distanceThreshold) count++;
    }
    // `<=` lets a later city win a tie.
    if (count <= bestCount) {
      bestCity = city;
      bestCount = count;
    }
  }
  return bestCity;
}
