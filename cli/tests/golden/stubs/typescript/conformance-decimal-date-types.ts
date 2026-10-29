// Conformance: decimal and date round-trip. Statement: .statements/conformance-decimal-date-types.md. Run: cstudy test conformance-decimal-date-types
import { Decimal, type IsoDate } from "#support";

export class TypeEcho {
  constructor(label: string) {}

  echoDecimal(value: Decimal): Decimal {
    throw new Error("Not implemented");
  }

  echoDate(value: IsoDate): IsoDate {
    throw new Error("Not implemented");
  }

  echoDecimalArray(value: Decimal[]): Decimal[] {
    throw new Error("Not implemented");
  }

  echoDateArray(value: IsoDate[]): IsoDate[] {
    throw new Error("Not implemented");
  }

  echoDecimalMatrix(value: Decimal[][]): Decimal[][] {
    throw new Error("Not implemented");
  }

  echoDateMatrix(value: IsoDate[][]): IsoDate[][] {
    throw new Error("Not implemented");
  }

  echoDecimalList(value: Decimal[]): Decimal[] {
    throw new Error("Not implemented");
  }

  echoDateList(value: IsoDate[]): IsoDate[] {
    throw new Error("Not implemented");
  }
}
