pub struct VillageMap {
    label: Vec<usize>, // label[v]: the name of the group of village v
    members: Vec<i32>, // members[g]: how many villages carry label g
    groups: i32,
}

impl VillageMap {
    pub fn new(villages: i32) -> Self {
        let count = villages as usize;
        VillageMap {
            label: (0..count).collect(),
            members: vec![1; count],
            groups: villages,
        }
    }

    pub fn add_path(&mut self, a: i32, b: i32) -> bool {
        let keep = self.label[a as usize];
        let drop = self.label[b as usize];
        if keep == drop {
            return false;
        }
        // Every village of the dropped group has to learn its new label.
        for label in self.label.iter_mut() {
            if *label == drop {
                *label = keep;
            }
        }
        self.members[keep] += self.members[drop];
        self.groups -= 1;
        true
    }

    pub fn can_reach(&mut self, a: i32, b: i32) -> bool {
        self.label[a as usize] == self.label[b as usize]
    }

    pub fn group_size(&mut self, village: i32) -> i32 {
        self.members[self.label[village as usize]]
    }

    pub fn group_count(&mut self) -> i32 {
        self.groups
    }
}
