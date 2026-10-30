package parking_lot

import (
	"container/heap"
	"strconv"
)

const (
	secondsPerHour = 3600
	hoursPerDay    = 24
	dailyCapHours  = 8
)

type spotSize int

const (
	small spotSize = iota
	medium
	large
)

// vehicleType lists the spot sizes it fits, smallest first, and its hourly rate in cents.
type vehicleType struct {
	fits       []spotSize
	hourlyRate int64
}

var vehicleTypes = map[string]vehicleType{
	"MOTORCYCLE": {[]spotSize{small, medium, large}, 100},
	"CAR":        {[]spotSize{medium, large}, 250},
	"VAN":        {[]spotSize{large}, 400},
}

var spotSizes = map[rune]spotSize{'S': small, 'M': medium, 'L': large}

type spot struct {
	level, index int
}

func (s spot) label() string {
	return strconv.Itoa(s.level) + "-" + strconv.Itoa(s.index)
}

// spotHeap is a min-heap of spots ordered by level, then index.
type spotHeap []spot

func (h spotHeap) Len() int { return len(h) }
func (h spotHeap) Less(i, j int) bool {
	if h[i].level != h[j].level {
		return h[i].level < h[j].level
	}
	return h[i].index < h[j].index
}
func (h spotHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *spotHeap) Push(x any)   { *h = append(*h, x.(spot)) }
func (h *spotHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type ticket struct {
	id       string
	plate    string
	vehicle  vehicleType
	spot     spot
	parkedAt int64
}

type pricingPolicy interface {
	fee(vehicle vehicleType, parkedAt, leftAt int64) int64
}

// billableHours counts started hours, at least one.
func billableHours(parkedAt, leftAt int64) int64 {
	return max(1, (leftAt-parkedAt+secondsPerHour-1)/secondsPerHour)
}

type hourlyPricing struct{}

func (hourlyPricing) fee(vehicle vehicleType, parkedAt, leftAt int64) int64 {
	return billableHours(parkedAt, leftAt) * vehicle.hourlyRate
}

// dailyCapPricing is hourly, but each started day costs at most dailyCapHours hours.
type dailyCapPricing struct{}

func (dailyCapPricing) fee(vehicle vehicleType, parkedAt, leftAt int64) int64 {
	billable := billableHours(parkedAt, leftAt)
	days, hours := billable/hoursPerDay, billable%hoursPerDay
	dayCap := dailyCapHours * vehicle.hourlyRate
	return days*dayCap + min(hours*vehicle.hourlyRate, dayCap)
}

var pricingSchemes = map[string]pricingPolicy{
	"HOURLY":    hourlyPricing{},
	"DAILY_CAP": dailyCapPricing{},
}

// spotAllocator keeps the free spots per size and hands out the smallest fitting size, then the
// lowest level and index.
type spotAllocator struct {
	free  map[spotSize]*spotHeap
	sizes map[spot]spotSize
}

func newSpotAllocator(layout []string) *spotAllocator {
	a := &spotAllocator{
		free:  map[spotSize]*spotHeap{small: {}, medium: {}, large: {}},
		sizes: make(map[spot]spotSize),
	}
	for level, row := range layout {
		for index, code := range row {
			s := spot{level, index}
			size := spotSizes[code]
			a.sizes[s] = size
			*a.free[size] = append(*a.free[size], s)
		}
	}
	for _, spots := range a.free {
		heap.Init(spots)
	}
	return a
}

func (a *spotAllocator) allocate(vehicle vehicleType) (spot, bool) {
	for _, size := range vehicle.fits {
		if spots := a.free[size]; spots.Len() > 0 {
			return heap.Pop(spots).(spot), true
		}
	}
	return spot{}, false
}

func (a *spotAllocator) release(s spot) {
	heap.Push(a.free[a.sizes[s]], s)
}

func (a *spotAllocator) freeCount(vehicle vehicleType) int {
	count := 0
	for _, size := range vehicle.fits {
		count += a.free[size].Len()
	}
	return count
}

type ParkingLot struct {
	allocator *spotAllocator
	pricing   pricingPolicy
	tickets   map[string]*ticket
	parked    map[string]*ticket // plate -> open ticket
	issued    int
}

func NewParkingLot(levels []string) *ParkingLot {
	return &ParkingLot{
		allocator: newSpotAllocator(levels),
		pricing:   hourlyPricing{},
		tickets:   make(map[string]*ticket),
		parked:    make(map[string]*ticket),
	}
}

func (l *ParkingLot) Park(timestamp int64, plate string, vehicleType string) string {
	vehicle, known := vehicleTypes[vehicleType]
	if _, taken := l.parked[plate]; !known || taken {
		return ""
	}
	s, ok := l.allocator.allocate(vehicle)
	if !ok {
		return ""
	}
	l.issued++
	t := &ticket{id: "T" + strconv.Itoa(l.issued), plate: plate, vehicle: vehicle, spot: s, parkedAt: timestamp}
	l.tickets[t.id] = t
	l.parked[plate] = t
	return t.id
}

func (l *ParkingLot) Leave(timestamp int64, ticketId string) int64 {
	t, ok := l.tickets[ticketId]
	if !ok {
		return -1
	}
	delete(l.tickets, ticketId)
	delete(l.parked, t.plate)
	l.allocator.release(t.spot)
	return l.pricing.fee(t.vehicle, t.parkedAt, timestamp)
}

func (l *ParkingLot) Locate(plate string) string {
	if t, ok := l.parked[plate]; ok {
		return t.spot.label()
	}
	return ""
}

func (l *ParkingLot) FreeSpots(vehicleType string) int {
	vehicle, known := vehicleTypes[vehicleType]
	if !known {
		return -1
	}
	return l.allocator.freeCount(vehicle)
}

func (l *ParkingLot) SetPricing(scheme string) bool {
	policy, ok := pricingSchemes[scheme]
	if !ok {
		return false
	}
	l.pricing = policy
	return true
}
