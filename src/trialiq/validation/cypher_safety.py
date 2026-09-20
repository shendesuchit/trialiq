
from typing import Any
import re


# Change Start
"""Initial safety validation for read-only Cypher queries."""


FORBIDDEN_KEYWORDS = (
    "CREATE",
    "MERGE",
    "SET",
    "DELETE",
    "REMOVE",
    "DROP",
    "LOAD CSV",
    "ALTER",
    "RENAME",
    "GRANT",
    "DENY",
    "REVOKE",
)

FORBIDDEN_PROCEDURE_PREFIXES = (
    "DBMS.",
    "APOC.",
)


def _remove_strings_and_comments(query: str) -> str:
    """Remove string literals and comments before keyword checks."""

    result: list[str] = []
    index = 0
    length = len(query)

    while index < length:
        character = query[index]

        if character in ("'", '"'):
            quote = character
            index += 1

            while index < length:
                if query[index] == "\\":
                    index += 2
                    continue

                if query[index] == quote:
                    index += 1
                    break

                index += 1

            result.append(" ")
            continue

        if query.startswith("//", index):
            newline_index = query.find("\n", index)

            if newline_index == -1:
                break

            index = newline_index + 1
            result.append("\n")
            continue

        if query.startswith("/*", index):
            end_index = query.find("*/", index + 2)

            if end_index == -1:
                break

            index = end_index + 2
            result.append(" ")
            continue

        result.append(character)
        index += 1

    return "".join(result)


def validate_read_only_cypher(
    query: Any,
) -> dict[str, Any]:
    """Validate a Cypher query against initial read-only rules."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(query, str):
        errors.append("Cypher query must be a string.")

        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    normalized_query = query.strip()

    if not normalized_query:
        errors.append("Cypher query is empty.")

        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    executable_query = _remove_strings_and_comments(
        normalized_query
    ).strip()

    if executable_query.endswith(";"):
        errors.append(
            "Multiple-statement execution is not permitted."
        )

    upper_query = executable_query.upper()

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(pattern, upper_query):
            errors.append(
                f"Forbidden Cypher operation detected: {keyword}."
            )

    for procedure_prefix in FORBIDDEN_PROCEDURE_PREFIXES:
        if procedure_prefix in upper_query:
            errors.append(
                "Potentially unsafe procedure invocation detected."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# Change End