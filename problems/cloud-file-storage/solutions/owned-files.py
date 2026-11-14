from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class _File:
    name: str
    size: int
    owner: str | None


@dataclass(slots=True)
class _User:
    capacity: int
    used: int = 0
    files: set[str] = field(default_factory=set)

    def fits(self, size: int) -> bool:
        return self.used + size <= self.capacity


def _largest_first(file: _File) -> tuple[int, str]:
    return -file.size, file.name


class CloudStorage:
    def __init__(self) -> None:
        self._files: dict[str, _File] = {}
        self._users: dict[str, _User] = {}
        self._backups: dict[str, list[_File]] = {}

    # Level 1
    def add_file(self, timestamp: int, name: str, size: int) -> bool:
        if name in self._files:
            return False
        self._store(_File(name, size, None))
        return True

    def get_file_size(self, timestamp: int, name: str) -> int:
        file = self._files.get(name)
        return -1 if file is None else file.size

    def delete_file(self, timestamp: int, name: str) -> int:
        file = self._files.get(name)
        if file is None:
            return -1
        self._discard(file)
        return file.size

    # Level 2
    def list_largest(self, timestamp: int, prefix: str, limit: int) -> list[str]:
        matching = (file for file in self._files.values() if file.name.startswith(prefix))
        return [f"{file.name}({file.size})" for file in sorted(matching, key=_largest_first)[:limit]]

    # Level 3
    def add_user(self, timestamp: int, user_id: str, capacity: int) -> bool:
        if user_id in self._users:
            return False
        self._users[user_id] = _User(capacity)
        return True

    def add_file_by(self, timestamp: int, user_id: str, name: str, size: int) -> int:
        user = self._users.get(user_id)
        if user is None or name in self._files or not user.fits(size):
            return -1
        self._store(_File(name, size, user_id))
        return user.capacity - user.used

    def update_capacity(self, timestamp: int, user_id: str, capacity: int) -> int:
        user = self._users.get(user_id)
        if user is None:
            return -1
        user.capacity = capacity
        removed = 0
        for file in sorted(self._owned_by(user), key=_largest_first):
            if user.used <= capacity:
                break
            self._discard(file)
            removed += 1
        return removed

    # Level 4
    def backup_user(self, timestamp: int, user_id: str) -> int:
        user = self._users.get(user_id)
        if user is None:
            return -1
        self._backups[user_id] = self._owned_by(user)
        return len(self._backups[user_id])

    def restore_user(self, timestamp: int, user_id: str) -> int:
        user = self._users.get(user_id)
        if user is None:
            return -1
        for file in self._owned_by(user):
            self._discard(file)
        restored = 0
        for file in sorted(self._backups.get(user_id, []), key=lambda saved: saved.name):
            if file.name not in self._files and user.fits(file.size):
                self._store(file)
                restored += 1
        return restored

    def _owned_by(self, user: _User) -> list[_File]:
        return [self._files[name] for name in user.files]

    def _store(self, file: _File) -> None:
        self._files[file.name] = file
        if file.owner is not None:
            user = self._users[file.owner]
            user.used += file.size
            user.files.add(file.name)

    def _discard(self, file: _File) -> None:
        del self._files[file.name]
        if file.owner is not None:
            user = self._users[file.owner]
            user.used -= file.size
            user.files.discard(file.name)
