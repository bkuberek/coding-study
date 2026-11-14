import { Decimal, type IsoDate } from "#support";

export class TypeEcho {
  constructor(label: string) {}

  echoDecimal(value: Decimal): Decimal {
    return value;
  }

  echoDate(value: IsoDate): IsoDate {
    return value;
  }

  echoDecimalArray(value: Decimal[]): Decimal[] {
    return value;
  }

  echoDateArray(value: IsoDate[]): IsoDate[] {
    return value;
  }

  echoDecimalMatrix(value: Decimal[][]): Decimal[][] {
    return value;
  }

  echoDateMatrix(value: IsoDate[][]): IsoDate[][] {
    return value;
  }

  echoDecimalList(value: Decimal[]): Decimal[] {
    return value;
  }

  echoDateList(value: IsoDate[]): IsoDate[] {
    return value;
  }
}
