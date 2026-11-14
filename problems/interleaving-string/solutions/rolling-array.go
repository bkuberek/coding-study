package interleaving_string

func isInterleave(s1 string, s2 string, s3 string) bool {
	if len(s1)+len(s2) != len(s3) {
		return false
	}
	// Swapping the sources does not change the answer, so let the row run along the shorter.
	longer, shorter := s1, s2
	if len(s1) < len(s2) {
		longer, shorter = s2, s1
	}
	// Before row i is processed, reach[j] tells whether longer[:i-1] and shorter[:j]
	// interleave to s3[:i-1+j]; afterwards it holds row i.
	reach := make([]bool, len(shorter)+1)
	for i := 0; i <= len(longer); i++ {
		for j := 0; j <= len(shorter); j++ {
			if i == 0 && j == 0 {
				reach[j] = true
				continue
			}
			fromLonger := i > 0 && reach[j] && longer[i-1] == s3[i+j-1]
			fromShorter := j > 0 && reach[j-1] && shorter[j-1] == s3[i+j-1]
			reach[j] = fromLonger || fromShorter
		}
	}
	return reach[len(shorter)]
}
