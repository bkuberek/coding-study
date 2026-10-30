package parking_lot

type ParkingLot struct {
	occupied []bool
	spotOf   map[string]int
}

func NewParkingLot(spots int) *ParkingLot {
	return &ParkingLot{occupied: make([]bool, spots), spotOf: map[string]int{}}
}

func (p *ParkingLot) Park(plate string) int {
	if _, parked := p.spotOf[plate]; parked {
		return -1
	}
	for spot, occupied := range p.occupied {
		if !occupied {
			p.occupied[spot] = true
			p.spotOf[plate] = spot
			return spot
		}
	}
	return -1
}

func (p *ParkingLot) Leave(plate string) bool {
	spot, parked := p.spotOf[plate]
	if !parked {
		return false
	}
	delete(p.spotOf, plate)
	p.occupied[spot] = false
	return true
}

func (p *ParkingLot) Available() int {
	return len(p.occupied) - len(p.spotOf)
}
