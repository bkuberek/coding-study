package conformance_hang

func waitFor(value int) int {
	for value < 0 {
	}
	return value
}
