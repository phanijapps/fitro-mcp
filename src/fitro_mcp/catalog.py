"""Reviewed operation catalog derived from the official Personal API Swagger page."""

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any
from urllib.parse import quote

from jsonschema import Draft202012Validator, FormatChecker

from fitro_mcp.errors import BridgeError


@dataclass(frozen=True)
class Operation:
    """A reviewed GET endpoint and its domain-scoped operation contract.

    ``name`` is the internal catalog key; discovery removes its get_ prefix.
    ``schema`` describes exact upstream parameter names. ``path_parameters``
    identifies substitutions; all remaining supplied values become query fields.
    Binary responses currently mean the documented ZIP activity download only.
    """

    name: str
    domain: str
    path: str
    description: str
    path_parameters: list[str]
    binary: bool
    schema: dict[str, Any]

    def prepare(self, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Validate before authentication, then safely bind path and query values."""
        validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        if next(validator.iter_errors(arguments), None) is not None:
            raise BridgeError("Invalid arguments. Consult this tool's input schema.")
        path = self.path
        query = dict(arguments)
        for name in self.path_parameters:
            path = path.replace("{" + name + "}", quote(str(query.pop(name)), safe=""))
        # Reject backwards date ranges, including the API's several naming conventions.
        for start, end in [
            ("startDate", "endDate"),
            ("fromDate", "toDate"),
            ("fromDate", "untilDate"),
        ]:
            if start in arguments and end in arguments and arguments[start] > arguments[end]:
                raise BridgeError("Start date must be on or before end date.")
        return path, query


def load_catalog() -> dict[str, Operation]:
    """Load the bundled allowlist, without network access or executable generation."""
    source = files("fitro_mcp").joinpath("data/operations.json").read_text()
    return {item["name"]: Operation(**item) for item in json.loads(source)}
