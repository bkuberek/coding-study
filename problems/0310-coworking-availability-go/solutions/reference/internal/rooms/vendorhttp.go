package rooms

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"time"
)

// requestLimit is the longest any vendor gets to answer one request, its whole body included.
const requestLimit = 1500 * time.Millisecond

// answer is what a vendor answered, whatever its status.
type answer struct {
	status int
	header http.Header
	body   []byte
}

func (a answer) ok() bool {
	return a.status >= http.StatusOK && a.status < http.StatusMultipleChoices
}

// get sends one request, and reads the whole answer within the limit every vendor gets.
func get(ctx context.Context, client *http.Client, url string) (answer, error) {
	ctx, cancel := context.WithTimeout(ctx, requestLimit)
	defer cancel()
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return answer{}, err
	}
	response, err := client.Do(request)
	if err != nil {
		return answer{}, fmt.Errorf("no answer from %s: %w", url, err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(response.Body)
	if err != nil {
		return answer{}, fmt.Errorf("no whole answer from %s: %w", url, err)
	}
	return answer{response.StatusCode, response.Header, body}, nil
}
