from models.variable import Variable


class CombinationCounter:

    def count(self, variables: list[Variable]) -> int:

        if not variables:
            return 1

        total = 1

        for variable in variables:
            total *= len(variable.values)

        return total