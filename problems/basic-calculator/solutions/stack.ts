export function calculate(s: string): number {
  const terms: number[] = []; // signed terms; the last one may still be multiplied or divided
  let number = 0;
  let operator = "+"; // the operator in front of the number being read
  for (let i = 0; i < s.length; i++) {
    const character = s[i];
    if (character >= "0" && character <= "9") {
      number = number * 10 + (character.charCodeAt(0) - 48);
    }
    if ("+-*/".includes(character) || i === s.length - 1) {
      if (operator === "+") {
        terms.push(number);
      } else if (operator === "-") {
        terms.push(-number);
      } else if (operator === "*") {
        terms.push((terms.pop() as number) * number);
      } else {
        // Math.trunc rounds toward zero, which matters for negative terms.
        terms.push(Math.trunc((terms.pop() as number) / number));
      }
      operator = character;
      number = 0;
    }
  }
  return terms.reduce((total, term) => total + term, 0);
}
