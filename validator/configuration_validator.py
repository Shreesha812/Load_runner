from models.configuration import Configuration


class ConfigurationValidator:

    def validate(self, configuration: Configuration) -> list[str]:

        errors = []

        if not configuration.test_definitions:
            errors.append("No valid test definitions found.")

        enabled_tests = [
            test
            for test in configuration.test_definitions
            if test.enabled
        ]

        if not enabled_tests:
            errors.append("No enabled test definitions found.")

        return errors