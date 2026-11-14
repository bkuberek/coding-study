use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};

const SECONDS_PER_HOUR: i64 = 3600;
const HOURS_PER_DAY: i64 = 24;
const DAILY_CAP_HOURS: i64 = 8;

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
enum SpotSize {
    Small,
    Medium,
    Large,
}

#[derive(Clone, Copy)]
enum VehicleType {
    Motorcycle,
    Car,
    Van,
}

impl VehicleType {
    fn parse(name: &str) -> Option<VehicleType> {
        match name {
            "MOTORCYCLE" => Some(VehicleType::Motorcycle),
            "CAR" => Some(VehicleType::Car),
            "VAN" => Some(VehicleType::Van),
            _ => None,
        }
    }

    /// The spot sizes this vehicle fits, smallest first.
    fn fits(self) -> &'static [SpotSize] {
        match self {
            VehicleType::Motorcycle => &[SpotSize::Small, SpotSize::Medium, SpotSize::Large],
            VehicleType::Car => &[SpotSize::Medium, SpotSize::Large],
            VehicleType::Van => &[SpotSize::Large],
        }
    }

    /// The hourly rate in cents.
    fn hourly_rate(self) -> i64 {
        match self {
            VehicleType::Motorcycle => 100,
            VehicleType::Car => 250,
            VehicleType::Van => 400,
        }
    }
}

/// Spots order by level, then index.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
struct Spot {
    level: usize,
    index: usize,
}

impl Spot {
    fn label(&self) -> String {
        format!("{}-{}", self.level, self.index)
    }
}

struct Ticket {
    plate: String,
    vehicle: VehicleType,
    spot: Spot,
    parked_at: i64,
}

trait PricingPolicy {
    fn fee(&self, vehicle: VehicleType, parked_at: i64, left_at: i64) -> i64;
}

/// Started hours, at least one.
fn billable_hours(parked_at: i64, left_at: i64) -> i64 {
    ((left_at - parked_at + SECONDS_PER_HOUR - 1) / SECONDS_PER_HOUR).max(1)
}

struct HourlyPricing;

impl PricingPolicy for HourlyPricing {
    fn fee(&self, vehicle: VehicleType, parked_at: i64, left_at: i64) -> i64 {
        billable_hours(parked_at, left_at) * vehicle.hourly_rate()
    }
}

/// Hourly, but each started day costs at most `DAILY_CAP_HOURS` hours.
struct DailyCapPricing;

impl PricingPolicy for DailyCapPricing {
    fn fee(&self, vehicle: VehicleType, parked_at: i64, left_at: i64) -> i64 {
        let billable = billable_hours(parked_at, left_at);
        let (days, hours) = (billable / HOURS_PER_DAY, billable % HOURS_PER_DAY);
        let cap = DAILY_CAP_HOURS * vehicle.hourly_rate();
        days * cap + (hours * vehicle.hourly_rate()).min(cap)
    }
}

fn pricing_scheme(name: &str) -> Option<Box<dyn PricingPolicy>> {
    match name {
        "HOURLY" => Some(Box::new(HourlyPricing)),
        "DAILY_CAP" => Some(Box::new(DailyCapPricing)),
        _ => None,
    }
}

/// Free spots per size; hands out the smallest fitting size, then the lowest level and index.
struct SpotAllocator {
    free: HashMap<SpotSize, BinaryHeap<Reverse<Spot>>>,
    sizes: HashMap<Spot, SpotSize>,
}

impl SpotAllocator {
    fn new(layout: &[String]) -> Self {
        let mut free: HashMap<SpotSize, BinaryHeap<Reverse<Spot>>> = HashMap::new();
        let mut sizes = HashMap::new();
        for (level, row) in layout.iter().enumerate() {
            for (index, code) in row.chars().enumerate() {
                let spot = Spot { level, index };
                let size = match code {
                    'S' => SpotSize::Small,
                    'M' => SpotSize::Medium,
                    _ => SpotSize::Large,
                };
                sizes.insert(spot, size);
                free.entry(size).or_default().push(Reverse(spot));
            }
        }
        SpotAllocator { free, sizes }
    }

    fn allocate(&mut self, vehicle: VehicleType) -> Option<Spot> {
        vehicle
            .fits()
            .iter()
            .find_map(|size| self.free.get_mut(size)?.pop())
            .map(|Reverse(spot)| spot)
    }

    fn release(&mut self, spot: Spot) {
        self.free
            .entry(self.sizes[&spot])
            .or_default()
            .push(Reverse(spot));
    }

    fn free_count(&self, vehicle: VehicleType) -> usize {
        vehicle
            .fits()
            .iter()
            .map(|size| self.free.get(size).map_or(0, BinaryHeap::len))
            .sum()
    }
}

pub struct ParkingLot {
    allocator: SpotAllocator,
    pricing: Box<dyn PricingPolicy>,
    tickets: HashMap<String, Ticket>,
    /// Plate to the id of its open ticket.
    parked: HashMap<String, String>,
    issued: usize,
}

impl ParkingLot {
    pub fn new(levels: Vec<String>) -> Self {
        ParkingLot {
            allocator: SpotAllocator::new(&levels),
            pricing: Box::new(HourlyPricing),
            tickets: HashMap::new(),
            parked: HashMap::new(),
            issued: 0,
        }
    }

    pub fn park(&mut self, timestamp: i64, plate: String, vehicle_type: String) -> String {
        let Some(vehicle) = VehicleType::parse(&vehicle_type) else {
            return String::new();
        };
        if self.parked.contains_key(&plate) {
            return String::new();
        }
        let Some(spot) = self.allocator.allocate(vehicle) else {
            return String::new();
        };
        self.issued += 1;
        let ticket_id = format!("T{}", self.issued);
        self.parked.insert(plate.clone(), ticket_id.clone());
        self.tickets.insert(
            ticket_id.clone(),
            Ticket {
                plate,
                vehicle,
                spot,
                parked_at: timestamp,
            },
        );
        ticket_id
    }

    pub fn leave(&mut self, timestamp: i64, ticket_id: String) -> i64 {
        let Some(ticket) = self.tickets.remove(&ticket_id) else {
            return -1;
        };
        self.parked.remove(&ticket.plate);
        self.allocator.release(ticket.spot);
        self.pricing
            .fee(ticket.vehicle, ticket.parked_at, timestamp)
    }

    pub fn locate(&mut self, plate: String) -> String {
        self.parked
            .get(&plate)
            .map_or_else(String::new, |ticket_id| {
                self.tickets[ticket_id].spot.label()
            })
    }

    pub fn free_spots(&mut self, vehicle_type: String) -> i32 {
        match VehicleType::parse(&vehicle_type) {
            Some(vehicle) => self.allocator.free_count(vehicle) as i32,
            None => -1,
        }
    }

    pub fn set_pricing(&mut self, scheme: String) -> bool {
        match pricing_scheme(&scheme) {
            Some(policy) => {
                self.pricing = policy;
                true
            }
            None => false,
        }
    }
}
