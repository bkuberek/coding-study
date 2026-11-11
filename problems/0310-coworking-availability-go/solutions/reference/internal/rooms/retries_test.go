package rooms

import (
	"context"
	"errors"
	"net/http"
	"testing"
	"time"
)

func TestTheRoomVendorsWaitComesFromWhatItAnswered(t *testing.T) {
	cases := []struct {
		name      string
		status    int
		header    http.Header
		wait      time.Duration
		askedMore bool
	}{
		{"a 5xx passes", http.StatusInternalServerError, nil, shortWait, true},
		{"a 503 passes", http.StatusServiceUnavailable, nil, shortWait, true},
		{"a 429 says how long", http.StatusTooManyRequests, http.Header{"Retry-After": {"2"}}, 2 * time.Second, true},
		{"a 429 without a number", http.StatusTooManyRequests, nil, shortWait, true},
		{"a 429 with a date", http.StatusTooManyRequests, http.Header{"Retry-After": {"Wed, 21 Oct 2026 07:28:00 GMT"}}, shortWait, true},
		{"a 403 will not change", http.StatusForbidden, nil, 0, false},
		{"a 200 is an answer", http.StatusOK, nil, 0, false},
	}
	for _, c := range cases {
		wait, again := roomVendorWaitBeforeRetry(answer{status: c.status, header: c.header})

		if wait != c.wait || again != c.askedMore {
			t.Errorf("%s: waits %v and asks again %v, want %v and %v", c.name, wait, again, c.wait, c.askedMore)
		}
	}
}

func TestTheAnnexAsksAgainOnlyWhenBusy(t *testing.T) {
	notOK, ok, retryAfter := false, true, 999.2
	busyAnswer := annexVendorBody{OK: &notOK, Error: &annexVendorError{busy, &retryAfter}}

	if wait, again := annexVendorWaitBeforeRetry(busyAnswer); wait != time.Second || !again {
		t.Errorf("busy: waits %v and asks again %v, want 1s and true", wait, again)
	}
	if _, again := annexVendorWaitBeforeRetry(annexVendorBody{OK: &ok}); again {
		t.Errorf("an answer: asks again")
	}
}

// counted answers each request with the next of answers, and counts the requests.
type counted struct {
	answers []int
	sent    int
}

func (c *counted) send() (answer, error) {
	c.sent++
	return answer{status: c.answers[min(c.sent, len(c.answers))-1]}, nil
}

func noWait(found answer) (time.Duration, bool) {
	return 0, found.status >= http.StatusInternalServerError
}

func TestAskingStopsAtTheLimit(t *testing.T) {
	vendor := &counted{answers: []int{500}}

	found, _ := ask(context.Background(), vendor.send, noWait, 3)

	if vendor.sent != 3 || found.status != http.StatusInternalServerError {
		t.Errorf("sent %d and kept %d, want 3 and 500", vendor.sent, found.status)
	}
}

func TestAskingStopsAtTheFirstAnswerWorthKeeping(t *testing.T) {
	vendor := &counted{answers: []int{500, 200, 500}}

	found, _ := ask(context.Background(), vendor.send, noWait, 3)

	if vendor.sent != 2 || found.status != http.StatusOK {
		t.Errorf("sent %d and kept %d, want 2 and 200", vendor.sent, found.status)
	}
}

func TestNoAnswerIsNotAskedAgain(t *testing.T) {
	sent := 0
	send := func() (answer, error) {
		sent++
		return answer{}, errors.New("no answer in time")
	}

	if _, err := ask(context.Background(), send, noWait, 3); err == nil || sent != 1 {
		t.Errorf("sent %d with %v, want 1 with the error", sent, err)
	}
}

func TestAWaitEndsWhenTheCallerGivesUp(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	vendor := &counted{answers: []int{500}}
	longWait := func(answer) (time.Duration, bool) { return time.Hour, true }

	if _, err := ask(ctx, vendor.send, longWait, 3); !errors.Is(err, context.Canceled) {
		t.Errorf("waited and got %v, want context.Canceled", err)
	}
}
