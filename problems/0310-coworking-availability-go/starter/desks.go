package main

import (
	"encoding/json"
	"os"
)

// deskInventory is the hot desks the space holds itself: how many are left on each day it sells.
type deskInventory map[string]int

// loadDesks reads the counts by day from the JSON file at path.
func loadDesks(path string) (deskInventory, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var desks deskInventory
	if err := json.Unmarshal(content, &desks); err != nil {
		return nil, err
	}
	return desks, nil
}

// availableOn is the desks left on day, written YYYY-MM-DD, and false when the day is not on sale.
func (d deskInventory) availableOn(day string) (int, bool) {
	left, onSale := d[day]
	return left, onSale
}
