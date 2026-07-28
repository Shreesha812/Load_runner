from generator.random_strategy import RandomStrategy
from generator.sequential_strategy import SequentialStrategy
from models.test_definition import TestDefinition


class CombinationGenerator:

    def __init__(self):
        self.sequential = SequentialStrategy()
        self.random = RandomStrategy()

    def generate(self, test_definition: TestDefinition):

        strategy = test_definition.strategy.lower()

        if strategy == "sequential":
            return self.sequential.generate(test_definition.variables)

        elif strategy == "random":
            return self.random.generate(test_definition.variables)

        raise ValueError(f"Unknown strategy: {strategy}")