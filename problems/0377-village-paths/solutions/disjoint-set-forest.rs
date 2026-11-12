pub struct VillageMap {
    parent: Vec<usize>, // parent[v] == v marks the leader of a group
    size: Vec<i32>,     // size[r]: villages in the group whose leader is r
    groups: i32,
}

impl VillageMap {
    pub fn new(villages: i32) -> Self {
        let count = villages as usize;
        VillageMap {
            parent: (0..count).collect(),
            size: vec![1; count],
            groups: villages,
        }
    }

    fn leader(&mut self, start: usize) -> usize {
        let mut root = start;
        while self.parent[root] != root {
            root = self.parent[root];
        }
        // Path compression: send everything passed on the way straight to the leader.
        let mut village = start;
        while self.parent[village] != root {
            let next = self.parent[village];
            self.parent[village] = root;
            village = next;
        }
        root
    }

    pub fn add_path(&mut self, a: i32, b: i32) -> bool {
        let mut leader_a = self.leader(a as usize);
        let mut leader_b = self.leader(b as usize);
        if leader_a == leader_b {
            return false;
        }
        if self.size[leader_a] < self.size[leader_b] {
            std::mem::swap(&mut leader_a, &mut leader_b);
        }
        self.parent[leader_b] = leader_a; // union by size: the smaller group joins the larger
        self.size[leader_a] += self.size[leader_b];
        self.groups -= 1;
        true
    }

    pub fn can_reach(&mut self, a: i32, b: i32) -> bool {
        self.leader(a as usize) == self.leader(b as usize)
    }

    pub fn group_size(&mut self, village: i32) -> i32 {
        let leader = self.leader(village as usize);
        self.size[leader]
    }

    pub fn group_count(&mut self) -> i32 {
        self.groups
    }
}
