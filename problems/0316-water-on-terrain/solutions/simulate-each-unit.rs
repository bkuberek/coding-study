const STAY: i32 = -1;
const SPILL: i32 = -2;

/// Water is kept as a depth per column, and a column's level is its height plus its water.
///
/// One unit of water is one walk: try to the left, then to the right, one column at a time and
/// never uphill, and note where the final flat stretch of the walk begins. The walk either reaches
/// an edge (the unit falls off), ends lower than it began (the unit settles at the start of the
/// final flat stretch) or ends where it began (this direction does nothing).
pub struct Terrain {
    heights: Vec<i32>,
    depths: Vec<i32>,
    spilled_units: i32,
}

impl Terrain {
    pub fn new(heights: Vec<i32>) -> Self {
        let depths = vec![0; heights.len()];
        Terrain { heights, depths, spilled_units: 0 }
    }

    // Level 1
    pub fn render(&mut self) -> Vec<String> {
        self.picture(0, self.heights.len() as i32 - 1)
    }

    pub fn tallest(&mut self) -> i32 {
        self.heights.iter().copied().max().unwrap_or(0).max(0)
    }

    // Level 2
    pub fn pour(&mut self, column: i32) -> Vec<i32> {
        self.drop_unit(column as usize);
        self.depths.clone()
    }

    pub fn water(&mut self) -> Vec<i32> {
        self.depths.clone()
    }

    pub fn spilled(&mut self) -> i32 {
        self.spilled_units
    }

    // Level 3
    pub fn pour_many(&mut self, column: i32, units: i32) -> Vec<i32> {
        for _ in 0..units {
            self.drop_unit(column as usize);
        }
        self.depths.clone()
    }

    // Level 4
    pub fn render_window(&mut self, first: i32, last: i32) -> Vec<String> {
        self.picture(first, last)
    }

    fn level(&self, column: usize) -> i32 {
        self.heights[column] + self.depths[column]
    }

    fn drop_unit(&mut self, column: usize) {
        for step in [-1, 1] {
            let landing = self.walk(column, step);
            if landing == SPILL {
                self.spilled_units += 1;
                return;
            }
            if landing != STAY {
                self.depths[landing as usize] += 1;
                return;
            }
        }
        self.depths[column] += 1;
    }

    fn walk(&self, column: usize, step: i32) -> i32 {
        let mut at = column as i32;
        let mut flat_start = column;
        loop {
            let ahead = at + step;
            if ahead < 0 || ahead >= self.heights.len() as i32 {
                return SPILL;
            }
            let (ahead_level, at_level) = (self.level(ahead as usize), self.level(at as usize));
            if ahead_level > at_level {
                break;
            }
            if ahead_level < at_level {
                flat_start = ahead as usize;
            }
            at = ahead;
        }
        if self.level(flat_start) < self.level(column) {
            flat_start as i32
        } else {
            STAY
        }
    }

    fn picture(&self, first: i32, last: i32) -> Vec<String> {
        let top = (0..self.heights.len()).map(|column| self.level(column)).max().unwrap_or(0);
        let mut rows = Vec::new();
        for row in (1..=top).rev() {
            let mut cells = String::new();
            for column in first..=last {
                let column = column as usize;
                if self.heights[column] >= row {
                    cells.push('#');
                } else if self.level(column) >= row {
                    cells.push('~');
                } else {
                    cells.push('.');
                }
            }
            rows.push(cells);
        }
        rows
    }
}
