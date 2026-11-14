class ParkingLot:
    def __init__(self, spots: int) -> None:
        self._occupied = [False] * spots
        self._spot_of: dict[str, int] = {}

    def park(self, plate: str) -> int:
        if plate in self._spot_of:
            return -1
        for spot, occupied in enumerate(self._occupied):
            if not occupied:
                self._occupied[spot] = True
                self._spot_of[plate] = spot
                return spot
        return -1

    def leave(self, plate: str) -> bool:
        spot = self._spot_of.pop(plate, None)
        if spot is None:
            return False
        self._occupied[spot] = False
        return True

    def available(self) -> int:
        return len(self._occupied) - len(self._spot_of)
