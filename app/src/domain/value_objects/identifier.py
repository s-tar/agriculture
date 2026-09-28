from dataclasses import dataclass


@dataclass
class Identifier[T]:
    def __init__(self, value: T):
        self.value = value

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False

        return self.value == other.value

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash((type(self), self.value))
