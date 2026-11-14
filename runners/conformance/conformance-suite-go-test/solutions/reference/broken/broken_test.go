// A test file that does not compile: its package is one error, and the other packages still run.
package broken

import "testing"

func TestBroken(t *testing.T) {
	undefinedInConformance()
}
