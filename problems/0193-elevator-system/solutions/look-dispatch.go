package elevator_system

import (
	"sort"
	"strconv"
)

type direction int

const (
	down direction = -1
	idle direction = 0
	up   direction = 1
)

func (d direction) String() string {
	switch d {
	case up:
		return "UP"
	case down:
		return "DOWN"
	}
	return "IDLE"
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// car is one elevator car: a floor, a direction and a set of stops, moved by the LOOK rule.
type car struct {
	floor     int
	direction direction
	stops     map[int]struct{}
}

func newCar() *car {
	return &car{stops: make(map[int]struct{})}
}

func (c *car) addStop(floor int) {
	if c.direction == idle && floor == c.floor {
		return // already there: the doors open at once
	}
	c.stops[floor] = struct{}{}
}

func (c *car) tick() {
	if len(c.stops) == 0 {
		c.direction = idle
		return
	}
	if c.direction == idle {
		c.direction = down
		if c.nearestStop() > c.floor {
			c.direction = up
		}
	}
	c.floor += int(c.direction)
	delete(c.stops, c.floor)
	if len(c.stops) == 0 {
		c.direction = idle
	} else if !c.hasStopAhead() {
		c.direction = -c.direction
	}
}

// nearestStop returns the closest stop, the higher one on a tie.
func (c *car) nearestStop() int {
	best, first := 0, true
	for stop := range c.stops {
		distance, bestDistance := abs(stop-c.floor), abs(best-c.floor)
		if first || distance < bestDistance || (distance == bestDistance && stop > best) {
			best, first = stop, false
		}
	}
	return best
}

func (c *car) hasStopAhead() bool {
	for stop := range c.stops {
		if (stop-c.floor)*int(c.direction) > 0 {
			return true
		}
	}
	return false
}

// turningPoint returns the last stop the car reaches before it turns: the highest while going up,
// the lowest while going down.
func (c *car) turningPoint() int {
	turn, first := 0, true
	for stop := range c.stops {
		if first || (c.direction == up && stop > turn) || (c.direction == down && stop < turn) {
			turn, first = stop, false
		}
	}
	return turn
}

// travelTo returns the floors the car travels before reaching floor under the LOOK rule.
func (c *car) travelTo(floor int) int {
	if c.direction == idle || (floor-c.floor)*int(c.direction) > 0 {
		return abs(floor - c.floor)
	}
	turn := c.turningPoint()
	return abs(turn-c.floor) + abs(turn-floor)
}

func (c *car) status() string {
	return strconv.Itoa(c.floor) + ":" + c.direction.String()
}

type dispatchStrategy interface {
	choose(cars []*car, floor int) int
}

type nearestCar struct{}

func (nearestCar) choose(cars []*car, floor int) int {
	best, bestTravel := 0, cars[0].travelTo(floor)
	for index := 1; index < len(cars); index++ {
		if travel := cars[index].travelTo(floor); travel < bestTravel {
			best, bestTravel = index, travel
		}
	}
	return best
}

type roundRobin struct {
	next int
}

func (r *roundRobin) choose(cars []*car, floor int) int {
	chosen := r.next
	r.next = (r.next + 1) % len(cars)
	return chosen
}

type ElevatorSystem struct {
	cars     []*car
	floors   int
	strategy dispatchStrategy
}

func NewElevatorSystem(cars int, floors int) *ElevatorSystem {
	system := &ElevatorSystem{floors: floors, strategy: nearestCar{}}
	for i := 0; i < cars; i++ {
		system.cars = append(system.cars, newCar())
	}
	return system
}

func (s *ElevatorSystem) Call(floor int, direction string) int {
	if !s.validFloor(floor) || !s.canTravel(floor, direction) {
		return -1
	}
	chosen := s.strategy.choose(s.cars, floor)
	s.cars[chosen].addStop(floor)
	return chosen
}

func (s *ElevatorSystem) Select(car int, floor int) bool {
	if !s.validCar(car) || !s.validFloor(floor) {
		return false
	}
	s.cars[car].addStop(floor)
	return true
}

func (s *ElevatorSystem) Step(ticks int) {
	for i := 0; i < ticks; i++ {
		for _, c := range s.cars {
			c.tick()
		}
	}
}

func (s *ElevatorSystem) Status(car int) string {
	if !s.validCar(car) {
		return ""
	}
	return s.cars[car].status()
}

func (s *ElevatorSystem) Stops(car int) []int {
	if !s.validCar(car) {
		return []int{}
	}
	stops := make([]int, 0, len(s.cars[car].stops))
	for stop := range s.cars[car].stops {
		stops = append(stops, stop)
	}
	sort.Ints(stops)
	return stops
}

func (s *ElevatorSystem) SetStrategy(name string) bool {
	switch name {
	case "NEAREST":
		s.strategy = nearestCar{}
	case "ROUND_ROBIN":
		s.strategy = &roundRobin{}
	default:
		return false
	}
	return true
}

func (s *ElevatorSystem) validCar(car int) bool {
	return 0 <= car && car < len(s.cars)
}

func (s *ElevatorSystem) validFloor(floor int) bool {
	return 0 <= floor && floor < s.floors
}

func (s *ElevatorSystem) canTravel(floor int, direction string) bool {
	switch direction {
	case "UP":
		return floor < s.floors-1
	case "DOWN":
		return floor > 0
	}
	return false
}
