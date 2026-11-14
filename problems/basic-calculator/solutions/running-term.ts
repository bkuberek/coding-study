export function calculate(s: string): number {
  let total = 0; // the sum of the finished terms
  let term = 0; // the signed term still being built
  let number = 0;
  let operator = "+"; // the operator in front of the number being read
  for (let i = 0; i < s.length; i++) {
    const character = s[i];
    if (character >= "0" && character <= "9") {
      number = number * 10 + (character.charCodeAt(0) - 48);
    }
    if ("+-*/".includes(character) || i === s.length - 1) {
      if (operator === "+" || operator === "-") {
        total += term;
        term = operator === "+" ? number : -number;
      } else if (operator === "*") {
        term *= number;
      } else {
        // Math.trunc rounds toward zero, which matters for negative terms.
        term = Math.trunc(term / number);
      }
      operator = character;
      number = 0;
    }
  }
  return total + term;
}
