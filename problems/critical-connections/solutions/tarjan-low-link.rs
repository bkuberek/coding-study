struct Search<'a> {
    adjacency: &'a [Vec<usize>],
    /// discovered[v] is the order in which v was first reached (-1: not yet).
    discovered: Vec<i32>,
    /// low[v] is the earliest discovery time reachable from v's subtree using at most one
    /// cable that is not a tree edge.
    low: Vec<i32>,
    bridges: Vec<Vec<i32>>,
    clock: i32,
}

impl Search<'_> {
    fn visit(&mut self, server: usize, parent: Option<usize>) {
        self.discovered[server] = self.clock;
        self.low[server] = self.clock;
        self.clock += 1;
        let adjacency = self.adjacency;
        for &neighbor in &adjacency[server] {
            if Some(neighbor) == parent {
                continue; // the tree edge we arrived by is not a way back
            }
            if self.discovered[neighbor] == -1 {
                self.visit(neighbor, Some(server));
                self.low[server] = self.low[server].min(self.low[neighbor]);
                if self.low[neighbor] > self.discovered[server] {
                    self.bridges.push(vec![server as i32, neighbor as i32]);
                }
            } else {
                self.low[server] = self.low[server].min(self.discovered[neighbor]);
            }
        }
    }
}

pub fn critical_connections(n: i32, connections: Vec<Vec<i32>>) -> Vec<Vec<i32>> {
    let n = n as usize;
    let mut adjacency: Vec<Vec<usize>> = vec![Vec::new(); n];
    for cable in &connections {
        let (a, b) = (cable[0] as usize, cable[1] as usize);
        adjacency[a].push(b);
        adjacency[b].push(a);
    }
    let mut search = Search {
        adjacency: &adjacency,
        discovered: vec![-1; n],
        low: vec![0; n],
        bridges: Vec::new(),
        clock: 0,
    };
    search.visit(0, None);
    search.bridges
}
