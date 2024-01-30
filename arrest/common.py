import enum


class StrEnum(str, enum.Enum):
    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.__repr__()


class Exit(int, enum.Enum):
    """Exit reasons."""

    OK = 0
    ERROR = 1
    KeyboardInterrupt = 2
