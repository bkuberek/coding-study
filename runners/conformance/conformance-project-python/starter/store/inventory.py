"""The entry class: `cstudy` imports `Inventory` from `store.inventory`."""


class Inventory:
    def add(self, name: str, count: int) -> int:
        raise NotImplementedError

    def label(self, name: str) -> str:
        raise NotImplementedError
