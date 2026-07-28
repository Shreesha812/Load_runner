import random

from models.variable import Variable


class RandomStrategy:

    def generate(self, variables: list[Variable]):

        while True:

            combination = {}

            for variable in variables:

                combination[variable.name] = random.choice(variable.values)

            yield combination
