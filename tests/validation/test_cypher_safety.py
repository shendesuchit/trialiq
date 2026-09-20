from trialiq.validation.cypher_safety import (
    validate_read_only_cypher,
)
# Change Start


def test_semicolon_inside_string_is_handled():
    result = validate_read_only_cypher(
        "RETURN 'hello;world' AS value"
    )

    assert result["valid"] is True


def test_keyword_inside_string_is_handled():
    result = validate_read_only_cypher(
        "RETURN 'CREATE a node' AS value"
    )

    assert result["valid"] is True


def test_comment_with_create_is_handled():
    result = validate_read_only_cypher(
        "// CREATE a node\nRETURN 1 AS value"
    )

    assert result["valid"] is True


def test_delete_query_is_rejected():
    result = validate_read_only_cypher(
        "MATCH (n) DELETE n"
    )

    assert result["valid"] is False


def test_merge_query_is_rejected():
    result = validate_read_only_cypher(
        "MERGE (n:Trial {nct_id: 'NCT00000001'}) RETURN n"
    )

    assert result["valid"] is False


# Change End