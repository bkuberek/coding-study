use std::collections::HashMap;

pub struct ParkingLot {
    occupied: Vec<bool>,
    spot_of: HashMap<String, usize>,
}

impl ParkingLot {
    pub fn new(spots: i32) -> Self {
        ParkingLot {
            occupied: vec![false; spots as usize],
            spot_of: HashMap::new(),
        }
    }

    pub fn park(&mut self, plate: String) -> i32 {
        if self.spot_of.contains_key(&plate) {
            return -1;
        }
        let Some(spot) = self.occupied.iter().position(|occupied| !occupied) else {
            return -1;
        };
        self.occupied[spot] = true;
        self.spot_of.insert(plate, spot);
        spot as i32
    }

    pub fn leave(&mut self, plate: String) -> bool {
        match self.spot_of.remove(&plate) {
            Some(spot) => {
                self.occupied[spot] = false;
                true
            }
            None => false,
        }
    }

    pub fn available(&mut self) -> i32 {
        (self.occupied.len() - self.spot_of.len()) as i32
    }
}
