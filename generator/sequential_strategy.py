from itertools import product

from models.variable import Variable

class SequentialStrategy:

    def generate(self, variables: list[Variable]):

        if not variables:
            yield {}
            return

        variable_names = [
            variable.name
            for variable in variables
        ]

        variable_values = [
            variable.values
            for variable in variables
        ]

        for combination in product(*variable_values):

            yield dict(zip(variable_names, combination))