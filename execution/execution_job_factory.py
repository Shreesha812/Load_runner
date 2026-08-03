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

        Variable placeholders (<varname>) are substituted in both the URL
        and each header value, not just the request body.
        """
        url = test_definition.url
        headers = dict(test_definition.headers)  # copy — don't mutate original

        if combination:
            for key, value in combination.items():
                placeholder = f"<{key}>"
                url = url.replace(placeholder, str(value))
                headers = {
                    k: v.replace(placeholder, str(value))
                    for k, v in headers.items()
                }

        return ExecutionJob(
            url=url,
            method=test_definition.method,
            headers=headers,
            body=rendered_body,
        )
