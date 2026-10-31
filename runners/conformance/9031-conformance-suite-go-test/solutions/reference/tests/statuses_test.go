// One test per outcome of a suite job, in the order go test runs them: a pass, an assertion
// failure, a table with a failing subtest, a panic and an exit that each end the test binary, so
// that its package runs again without the tests reported so far, output, and a hang that the hang
// guard ends, after which the suite restarts without it.
package tests_test

import (
	"fmt"
	"os"
	"testing"
	"time"

	probe "conformance-suite-go-test"
)

const exitCode = 3

func TestPasses(t *testing.T) {
	if got := probe.NewProbe().Ping(); got != "pong" {
		t.Fatalf("Ping() = %q, want pong", got)
	}
}

func TestFailsAnAssertion(t *testing.T) {
	if got := probe.NewProbe().Ping(); got != "ping" {
		t.Errorf("Ping() = %q, want ping", got)
	}
}

func TestTable(t *testing.T) {
	t.Run("ok", func(t *testing.T) {})
	t.Run("bad", func(t *testing.T) { t.Error("conformance subtest failure") })
}

func TestPanics(t *testing.T) {
	panic("conformance failure")
}

func TestPrints(t *testing.T) {
	fmt.Println("conformance output")
}

func TestEndsTheProcess(t *testing.T) {
	os.Exit(exitCode)
}

func TestHangs(t *testing.T) {
	time.Sleep(time.Hour)
}
