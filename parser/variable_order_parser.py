class VariableOrderParser:

    def parse(self, order_text: str) -> list[str]:

        if not order_text:
            return []

        return [
            variable.strip()
            for variable in order_text.split(",")
            if variable.strip()
        ]