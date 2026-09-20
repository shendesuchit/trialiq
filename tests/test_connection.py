
# Change Start
import pytest

from trialiq.graph.connection import Neo4jConnection


pytestmark = pytest.mark.integration


def test_neo4j_connectivity():
    """Verify connectivity to the configured Neo4j database."""
    connection = Neo4jConnection()

    try:
        connection.verify_connectivity()
    finally:
        connection.close()


def test_neo4j_read_query():
    """Verify that a simple read query executes successfully."""
    connection = Neo4jConnection()

    try:
        records = connection.execute_read(
            "RETURN 1 AS connectivity_test"
        )

        assert records == [{"connectivity_test": 1}]
    finally:
        connection.close()
