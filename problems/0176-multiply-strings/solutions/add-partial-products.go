package multiply_strings

// timesDigit returns the little-endian digits of digits * factor.
func timesDigit(digits []int, factor int) []int {
	product := make([]int, 0, len(digits)+1)
	carry := 0
	for _, digit := range digits {
		value := digit*factor + carry
		product = append(product, value%10)
		carry = value / 10
	}
	if carry > 0 {
		product = append(product, carry)
	}
	return product
}

// add returns the little-endian digits of left + right.
func add(left, right []int) []int {
	length := max(len(left), len(right))
	total := make([]int, 0, length+1)
	carry := 0
	for position := 0; position < length; position++ {
		a, b := 0, 0
		if position < len(left) {
			a = left[position]
		}
		if position < len(right) {
			b = right[position]
		}
		value := a + b + carry
		total = append(total, value%10)
		carry = value / 10
	}
	if carry > 0 {
		total = append(total, carry)
	}
	return total
}

func multiply(num1 string, num2 string) string {
	if num1 == "0" || num2 == "0" {
		return "0"
	}
	first := make([]int, len(num1))
	for i := range num1 {
		first[len(num1)-1-i] = int(num1[i] - '0')
	}
	var total []int
	// School method: one row per digit of num2, shifted by its position.
	for shift := 0; shift < len(num2); shift++ {
		factor := int(num2[len(num2)-1-shift] - '0')
		row := append(make([]int, shift), timesDigit(first, factor)...)
		total = add(total, row)
	}
	text := make([]byte, len(total))
	for i, digit := range total {
		text[len(total)-1-i] = byte('0' + digit)
	}
	return string(text)
}
