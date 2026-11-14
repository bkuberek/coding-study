// The company's warehouse sites. The names and the rates are made up.

export interface Site {
  readonly id: string;
  readonly name: string;
  /** What an hour of labor costs at this site. */
  readonly laborRateCentsPerHour: number;
  /** What the site adds on top of the cost of parts, in hundredths of a percent: 250 is 2.5%. */
  readonly partsMarkupBasisPoints: number;
}

export const SEED_SITES: readonly Site[] = [
  { id: "WH-1", name: "Harbor Annex", laborRateCentsPerHour: 4250, partsMarkupBasisPoints: 250 },
  { id: "WH-2", name: "Ridge Depot", laborRateCentsPerHour: 3990, partsMarkupBasisPoints: 875 },
  { id: "WH-3", name: "Canal Yard", laborRateCentsPerHour: 5130, partsMarkupBasisPoints: 0 },
];

export class SiteDirectory {
  readonly #sites: readonly Site[];

  constructor(sites: readonly Site[]) {
    this.#sites = sites;
  }

  list(): readonly Site[] {
    return this.#sites;
  }

  get(id: string): Site | undefined {
    return this.#sites.find((site) => site.id === id);
  }
}
