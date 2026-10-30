package partition_labels

func partitionLabels(s string) []int {
	// Each letter occupies the span from its first to its last copy. Spans listed by first
	// occurrence are already sorted by start, so merging overlapping spans gives the pieces.
	var first, last [26]int
	for slot := range first {
		first[slot] = -1
	}
	var letters []int // slots of the letters, by first occurrence
	for index := 0; index < len(s); index++ {
		slot := s[index] - 'a'
		if first[slot] < 0 {
			first[slot] = index
			letters = append(letters, int(slot))
		}
		last[slot] = index
	}
	var sizes []int
	pieceStart, pieceEnd := 0, -1
	for _, slot := range letters {
		if first[slot] > pieceEnd {
			if pieceEnd >= 0 {
				sizes = append(sizes, pieceEnd-pieceStart+1)
			}
			pieceStart = first[slot]
		}
		pieceEnd = max(pieceEnd, last[slot])
	}
	return append(sizes, pieceEnd-pieceStart+1)
}
