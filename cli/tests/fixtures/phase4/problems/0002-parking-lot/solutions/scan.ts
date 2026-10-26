export class ParkingLot {
  private readonly occupied: boolean[];
  private readonly spotOf = new Map<string, number>();

  constructor(spots: number) {
    this.occupied = new Array<boolean>(spots).fill(false);
  }

  park(plate: string): number {
    if (this.spotOf.has(plate)) {
      return -1;
    }
    const spot = this.occupied.indexOf(false);
    if (spot === -1) {
      return -1;
    }
    this.occupied[spot] = true;
    this.spotOf.set(plate, spot);
    return spot;
  }

  leave(plate: string): boolean {
    const spot = this.spotOf.get(plate);
    if (spot === undefined) {
      return false;
    }
    this.occupied[spot] = false;
    this.spotOf.delete(plate);
    return true;
  }

  available(): number {
    return this.occupied.length - this.spotOf.size;
  }
}
