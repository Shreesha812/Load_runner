import json
import logging

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """
    Renders a request body template by substituting <variable> placeholders.

    JSON validation is opt-in via validate_json=True (default: False).
    This allows the renderer to work with any content type — JSON, XML,
    plain text, form-encoded bodies, etc.
    """

    def render(
        self,
        template: str,
        variables: dict[str, str],
        validate_json: bool = False,
    ) -> str:
        rendered = template

        for key, value in variables.items():
            rendered = rendered.replace(f"<{key}>", str(value))

        # Normalize doubled quotes that can appear after substitution
        rendered = rendered.replace('""', '"')

        if validate_json:
            try:
                json.loads(rendered)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Rendered template is not valid JSON: {e}\n"
                    f"Rendered body:\n{rendered}"
                ) from e

        logger.debug("Rendered template with variables: %s", list(variables.keys()))
        return rendered
