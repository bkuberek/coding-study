import { Decimal } from "#support";

const FIELDS = ["contractorId", "classCode", "payroll", "periodStart"];
// [0-9], never a shorthand class: the digits are ASCII only.
const CONTRACTOR_ID = /^[a-z0-9-]{1,20}$/;
const CLASS_CODE = /^[0-9]{4}$/;
const PAYROLL = /^[0-9]+(\.[0-9]{1,2})?$/;
const ISO_DAY = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
const MAX_PAYROLL = new Decimal(1_000_000_000);
const FIRST_DAY = "2000-01-01";
const LAST_DAY = "2099-12-31";

function checkPattern(value: string, pattern: RegExp): string {
  if (value === "") {
    return "missing";
  }
  return pattern.test(value) ? "" : "invalid";
}

function checkPayroll(value: string): string {
  const reason = checkPattern(value, PAYROLL);
  if (reason !== "") {
    return reason;
  }
  const amount = new Decimal(value);
  return amount.gt(new Decimal(0)) && amount.lte(MAX_PAYROLL) ? "" : "out-of-range";
}

function checkPeriodStart(value: string): string {
  const reason = checkPattern(value, ISO_DAY);
  if (reason !== "") {
    return reason;
  }
  // Date.parse rolls 2026-02-30 over to 2 March, so a real day must survive a round trip.
  // Year 0000 round-trips too, but it is not a real day (years run 0001 to 9999).
  const millis = Date.parse(value);
  if (value.startsWith("0000") || Number.isNaN(millis) || new Date(millis).toISOString().slice(0, 10) !== value) {
    return "invalid";
  }
  return value >= FIRST_DAY && value <= LAST_DAY ? "" : "out-of-range";
}

export function validateRows(rows: string[][]): string[] {
  const errors: string[] = [];
  const seenKeys = new Set<string>();
  rows.forEach((row, index) => {
    if (row.length !== FIELDS.length) {
      errors.push(`${index}:row:column-count`);
      return;
    }
    const [contractorId, classCode, payroll, periodStart] = row;
    const reasons = [
      checkPattern(contractorId, CONTRACTOR_ID),
      checkPattern(classCode, CLASS_CODE),
      checkPayroll(payroll),
      checkPeriodStart(periodStart),
    ];
    reasons.forEach((reason, column) => {
      if (reason !== "") {
        errors.push(`${index}:${FIELDS[column]}:${reason}`);
      }
    });
    if (reasons[0] === "" && reasons[1] === "" && reasons[3] === "") {
      const key = `${contractorId}|${classCode}|${periodStart}`; // valid fields never contain "|"
      if (seenKeys.has(key)) {
        errors.push(`${index}:row:duplicate`);
      }
      seenKeys.add(key);
    }
  });
  return errors;
}
