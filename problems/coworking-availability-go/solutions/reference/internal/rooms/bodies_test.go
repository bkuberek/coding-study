package rooms

import (
	"encoding/json"
	"reflect"
	"testing"
)

func roomVendorSlots(t *testing.T, text string) ([]Slot, error) {
	t.Helper()
	var body roomVendorBody
	if err := json.Unmarshal([]byte(text), &body); err != nil {
		t.Fatal(err)
	}
	return body.openSlots()
}

func TestTheRoomVendorsOpenSlotsAreFlattened(t *testing.T) {
	found, err := roomVendorSlots(t, `{"rooms": [{"id": "oak", "slots": [
		{"start": "09:00", "end": "10:00", "status": "open"},
		{"start": "10:00", "end": "11:00", "status": "booked"},
		{"status": "booked"}]}]}`)

	want := []Slot{{"oak", "09:00", "10:00", roomVendorName}}
	if err != nil || !reflect.DeepEqual(found, want) {
		t.Errorf("found %v and %v, want %v", found, err, want)
	}
}

func TestNoRoomsIsAnAnswerWhileNoListIsNot(t *testing.T) {
	if found, err := roomVendorSlots(t, `{"rooms": []}`); err != nil || len(found) != 0 {
		t.Errorf("an empty list: %v and %v, want no slots", found, err)
	}
	if _, err := roomVendorSlots(t, `{"status": "ok"}`); err == nil {
		t.Errorf("no list: no error")
	}
}

func TestAnOpenSlotNeedsItsTimes(t *testing.T) {
	if _, err := roomVendorSlots(t, `{"rooms": [{"id": "oak", "slots": [{"status": "open"}]}]}`); err == nil {
		t.Errorf("an open slot with no times: no error")
	}
}

func annexSlots(t *testing.T, text string) ([]Slot, error) {
	t.Helper()
	var body annexVendorBody
	if err := json.Unmarshal([]byte(text), &body); err != nil {
		t.Fatal(err)
	}
	return body.slots()
}

func TestTheAnnexsMinutesBecomeTimes(t *testing.T) {
	found, err := annexSlots(t, `{"ok": true, "result": {"spaces": [
		{"code": "A1", "open": [{"from_minute": 425, "minutes": 45}]}]}}`)

	want := []Slot{{"A1", "07:05", "07:50", annexVendorName}}
	if err != nil || !reflect.DeepEqual(found, want) {
		t.Errorf("found %v and %v, want %v", found, err, want)
	}
}

func TestTheAnnexsOtherFieldsAreNoAnswer(t *testing.T) {
	if _, err := annexSlots(t, `{"ok": true, "result": {"rooms": []}}`); err == nil {
		t.Errorf("ok with the wrong fields: no error")
	}
}

func TestTheAnnexDecliningIsNoAnswer(t *testing.T) {
	if _, err := annexSlots(t, `{"ok": false, "error": {"code": "DAY_CLOSED"}}`); err == nil {
		t.Errorf("ok: false: no error")
	}
}
