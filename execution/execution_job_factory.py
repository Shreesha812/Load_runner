from execution.execution_job import ExecutionJob
from models.test_definition import TestDefinition


class ExecutionJobFactory:

    def build(
        self,
        test_definition: TestDefinition,
        rendered_body: str,
        combination: dict | None = None,
    ) -> ExecutionJob:
        """
        Build an ExecutionJob from a TestDefinition and rendered body.

        If a combination dict is provided, variable placeholders in the URL
        (e.g. /users/<userId>) are also substituted.
        """
        url = test_definition.url
        if combination:
            for key, value in combination.items():
                url = url.replace(f"<{key}>", str(value))

        return ExecutionJob(
            url=url,
            method=test_definition.method,
            headers=test_definition.headers,
            body=rendered_body,
        )
