class LevelStore:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def put(self, key: str, value: str) -> None:
        self._values[key] = value

    def get(self, key: str) -> str:
        return self._values.get(key, "")

    def remove(self, key: str) -> bool:
        return self._values.pop(key, None) is not None

    def size(self) -> int:
        return len(self._values)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        return sorted(key for key in self._values if key.startswith(prefix))
