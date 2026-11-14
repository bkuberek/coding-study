// The parts used on each work order: a child table, joined by `workOrderId`.

export interface PartLine {
  readonly workOrderId: string;
  readonly lineNumber: number;
  readonly sku: string;
  readonly quantity: number;
  readonly unitCostCents: number;
}

export class PartStore {
  readonly #lines: PartLine[] = [];

  add(workOrderId: string, part: Pick<PartLine, "sku" | "quantity" | "unitCostCents">): PartLine {
    const lineNumber = this.forOrder(workOrderId).length + 1;
    const line = { workOrderId, lineNumber, ...part };
    this.#lines.push(line);
    return line;
  }

  forOrder(workOrderId: string): PartLine[] {
    return this.#lines.filter((line) => line.workOrderId === workOrderId);
  }
}
