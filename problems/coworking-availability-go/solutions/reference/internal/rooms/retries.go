package rooms

import (
	"context"
	"time"
)

// ask sends until asking again will not help, or maxRequests are spent, and gives the last
// answer. waitBeforeRetry reads an answer and gives the wait before asking again, or false when
// asking again will not help; the wait starts once the answer has arrived, and ends early when
// ctx does. An error from send ends the asking: no answer in time is not worth another try.
func ask[T any](
	ctx context.Context,
	send func() (T, error),
	waitBeforeRetry func(T) (time.Duration, bool),
	maxRequests int,
) (T, error) {
	found, err := send()
	for sent := 1; err == nil && sent < maxRequests; sent++ {
		wait, again := waitBeforeRetry(found)
		if !again {
			break
		}
		if err = sleep(ctx, wait); err == nil {
			found, err = send()
		}
	}
	return found, err
}

func sleep(ctx context.Context, wait time.Duration) error {
	timer := time.NewTimer(wait)
	defer timer.Stop()
	select {
	case <-timer.C:
		return nil
	case <-ctx.Done():
		return context.Cause(ctx)
	}
}
