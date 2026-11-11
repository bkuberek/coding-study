package rooms

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"time"
)

const (
	annexVendorName        = "annex-vendor"
	annexVendorMaxRequests = 2
	busy                   = "BUSY"
	minutesPerHour         = 60
)

// AnnexVendor sells the rooms of the building next door. It says most of what it means in the
// body of a 200, and its 5xx means down for maintenance.
type AnnexVendor struct {
	spaces string
	client *http.Client
}

// NewAnnexVendor is the annex vendor at baseURL.
func NewAnnexVendor(baseURL string) AnnexVendor {
	return AnnexVendor{spaces: baseURL + "/v2/spaces/open", client: &http.Client{}}
}

func (AnnexVendor) Name() string {
	return annexVendorName
}

func (v AnnexVendor) OpenSlots(ctx context.Context, day time.Time) ([]Slot, error) {
	url := v.spaces + "?day=" + day.Format("20060102")
	send := func() (annexVendorBody, error) { return v.body(ctx, url) }
	found, err := ask(ctx, send, annexVendorWaitBeforeRetry, annexVendorMaxRequests)
	if err != nil {
		return nil, err
	}
	return found.slots()
}

// body is the vendor's answer, read. Any status but 2xx ends the asking, since its 5xx means
// down for maintenance.
func (v AnnexVendor) body(ctx context.Context, url string) (annexVendorBody, error) {
	found, err := get(ctx, v.client, url)
	if err != nil {
		return annexVendorBody{}, err
	}
	if !found.ok() {
		return annexVendorBody{}, fmt.Errorf("%s answered %d", annexVendorName, found.status)
	}
	var body annexVendorBody
	if err := json.Unmarshal(found.body, &body); err != nil || body.OK == nil {
		return annexVendorBody{}, undocumented(annexVendorName, "no answer with ok")
	}
	return body, nil
}

// annexVendorWaitBeforeRetry is how long the vendor asks you to wait before asking again, and
// false when it asks for no such thing.
func annexVendorWaitBeforeRetry(found annexVendorBody) (time.Duration, bool) {
	failure := found.Error
	if *found.OK || failure == nil || failure.Code != busy || failure.RetryAfterMs == nil {
		return 0, false
	}
	return time.Duration(math.Ceil(*failure.RetryAfterMs)) * time.Millisecond, true
}

// annexVendorBody is the vendor's answer as its API documents it: a result when ok, an error
// when not. Pointers and lists left out decode as nil, which is how a missing part shows.
type annexVendorBody struct {
	OK     *bool              `json:"ok"`
	Result *annexVendorResult `json:"result"`
	Error  *annexVendorError  `json:"error"`
}

type annexVendorResult struct {
	Spaces []struct {
		Code string `json:"code"`
		Open []struct {
			FromMinute *int `json:"from_minute"`
			Minutes    *int `json:"minutes"`
		} `json:"open"`
	} `json:"spaces"`
}

type annexVendorError struct {
	Code         string   `json:"code"`
	RetryAfterMs *float64 `json:"retry_after_ms"`
}

// slots is every slot listed, all of which can be booked, or an error when the vendor declined
// or left out a part its API promises.
func (b annexVendorBody) slots() ([]Slot, error) {
	if !*b.OK {
		return nil, fmt.Errorf("%s declined to answer: %+v", annexVendorName, b.Error)
	}
	if b.Result == nil || b.Result.Spaces == nil {
		return nil, undocumented(annexVendorName, "no spaces")
	}
	slots := []Slot{}
	for _, space := range b.Result.Spaces {
		if space.Code == "" || space.Open == nil {
			return nil, undocumented(annexVendorName, "a space with no code or no open times")
		}
		for _, window := range space.Open {
			if window.FromMinute == nil || window.Minutes == nil {
				return nil, undocumented(annexVendorName, "an open time with no start or length")
			}
			start, end := *window.FromMinute, *window.FromMinute+*window.Minutes
			slots = append(slots, Slot{space.Code, clock(start), clock(end), annexVendorName})
		}
	}
	return slots, nil
}

// clock is minutes past midnight as HH:MM: 425 is 07:05.
func clock(minutes int) string {
	return fmt.Sprintf("%02d:%02d", minutes/minutesPerHour, minutes%minutesPerHour)
}
