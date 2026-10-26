export function removeKDigits(num: string, k: number): string {
  const digits = num.split("");
  for (let removed = 0; removed < k; removed++) {
    // The first digit larger than its successor, or the last digit if none is.
    let peak = 0;
    while (peak + 1 < digits.length && digits[peak] <= digits[peak + 1]) {
      peak++;
    }
    digits.splice(peak, 1);
  }
  const result = digits.join("").replace(/^0+/, "");
  return result === "" ? "0" : result;
}
