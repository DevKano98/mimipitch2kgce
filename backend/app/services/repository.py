from typing import Protocol


class Repository(Protocol):
    def init(self) -> None: ...
