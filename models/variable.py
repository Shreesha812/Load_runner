from dataclasses import dataclass, field


@dataclass
class Variable:
    """
    Represents a variable defined in the Excel configuration.

    Example:
        Name: Fruit
        Values: ["Apple", "Banana", "Orange"]
    """

    name: str
    values: list[str] = field(default_factory=list)