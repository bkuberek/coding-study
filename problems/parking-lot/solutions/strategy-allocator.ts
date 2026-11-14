const SECONDS_PER_HOUR = 3600;
const HOURS_PER_DAY = 24;
const DAILY_CAP_HOURS = 8;

type SpotSize = "S" | "M" | "L";

interface VehicleType {
  readonly fits: readonly SpotSize[]; // smallest first
  readonly hourlyRate: number; // cents
}

const VEHICLE_TYPES = new Map<string, VehicleType>([
  ["MOTORCYCLE", { fits: ["S", "M", "L"], hourlyRate: 100 }],
  ["CAR", { fits: ["M", "L"], hourlyRate: 250 }],
  ["VAN", { fits: ["L"], hourlyRate: 400 }],
]);

class Spot {
  readonly level: number;
  readonly index: number;

  constructor(level: number, index: number) {
    this.level = level;
    this.index = index;
  }

  compareTo(other: Spot): number {
    return this.level - other.level || this.index - other.index;
  }

  label(): string {
    return `${this.level}-${this.index}`;
  }
}

interface Ticket {
  readonly id: string;
  readonly plate: string;
  readonly vehicle: VehicleType;
  readonly spot: Spot;
  readonly parkedAt: number;
}

interface PricingPolicy {
  fee(vehicle: VehicleType, parkedAt: number, leftAt: number): number;
}

// Started hours, at least one.
function billableHours(parkedAt: number, leftAt: number): number {
  return Math.max(1, Math.ceil((leftAt - parkedAt) / SECONDS_PER_HOUR));
}

class HourlyPricing implements PricingPolicy {
  fee(vehicle: VehicleType, parkedAt: number, leftAt: number): number {
    return billableHours(parkedAt, leftAt) * vehicle.hourlyRate;
  }
}

// Hourly, but each started day costs at most DAILY_CAP_HOURS hours.
class DailyCapPricing implements PricingPolicy {
  fee(vehicle: VehicleType, parkedAt: number, leftAt: number): number {
    const hours = billableHours(parkedAt, leftAt);
    const cap = DAILY_CAP_HOURS * vehicle.hourlyRate;
    const days = Math.floor(hours / HOURS_PER_DAY);
    return days * cap + Math.min((hours % HOURS_PER_DAY) * vehicle.hourlyRate, cap);
  }
}

const PRICING_SCHEMES = new Map<string, () => PricingPolicy>([
  ["HOURLY", () => new HourlyPricing()],
  ["DAILY_CAP", () => new DailyCapPricing()],
]);

// Free spots per size, each kept sorted by level and index.
class SpotAllocator {
  private readonly free = new Map<SpotSize, Spot[]>([["S", []], ["M", []], ["L", []]]);
  private readonly sizes = new Map<string, SpotSize>();

  constructor(layout: readonly string[]) {
    layout.forEach((row, level) => {
      [...row].forEach((code, index) => {
        const spot = new Spot(level, index);
        this.sizes.set(spot.label(), code as SpotSize);
        this.freeOf(code as SpotSize).push(spot);
      });
    });
  }

  allocate(vehicle: VehicleType): Spot | null {
    for (const size of vehicle.fits) {
      const spot = this.freeOf(size).shift();
      if (spot !== undefined) {
        return spot;
      }
    }
    return null;
  }

  release(spot: Spot): void {
    const spots = this.freeOf(this.sizes.get(spot.label()) ?? "L");
    let low = 0;
    let high = spots.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (spots[middle].compareTo(spot) < 0) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    spots.splice(low, 0, spot);
  }

  freeCount(vehicle: VehicleType): number {
    return vehicle.fits.reduce((total, size) => total + this.freeOf(size).length, 0);
  }

  private freeOf(size: SpotSize): Spot[] {
    return this.free.get(size) ?? [];
  }
}

export class ParkingLot {
  private readonly allocator: SpotAllocator;
  private pricing: PricingPolicy = new HourlyPricing();
  private readonly tickets = new Map<string, Ticket>();
  private readonly parked = new Map<string, Ticket>(); // plate -> open ticket
  private issued = 0;

  constructor(levels: string[]) {
    this.allocator = new SpotAllocator(levels);
  }

  park(timestamp: number, plate: string, vehicleType: string): string {
    const vehicle = VEHICLE_TYPES.get(vehicleType);
    if (vehicle === undefined || this.parked.has(plate)) {
      return "";
    }
    const spot = this.allocator.allocate(vehicle);
    if (spot === null) {
      return "";
    }
    this.issued++;
    const ticket: Ticket = { id: `T${this.issued}`, plate, vehicle, spot, parkedAt: timestamp };
    this.tickets.set(ticket.id, ticket);
    this.parked.set(plate, ticket);
    return ticket.id;
  }

  leave(timestamp: number, ticketId: string): number {
    const ticket = this.tickets.get(ticketId);
    if (ticket === undefined) {
      return -1;
    }
    this.tickets.delete(ticketId);
    this.parked.delete(ticket.plate);
    this.allocator.release(ticket.spot);
    return this.pricing.fee(ticket.vehicle, ticket.parkedAt, timestamp);
  }

  locate(plate: string): string {
    return this.parked.get(plate)?.spot.label() ?? "";
  }

  freeSpots(vehicleType: string): number {
    const vehicle = VEHICLE_TYPES.get(vehicleType);
    return vehicle === undefined ? -1 : this.allocator.freeCount(vehicle);
  }

  setPricing(scheme: string): boolean {
    const create = PRICING_SCHEMES.get(scheme);
    if (create === undefined) {
      return false;
    }
    this.pricing = create();
    return true;
  }
}
