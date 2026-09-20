# Neo4j Driver Connection

# Change Start
from contextlib import contextmanager
from collections.abc import Iterator

from neo4j import Driver, GraphDatabase, Transaction

from trialiq.config.settings import get_settings
from trialiq.validation.cypher_safety import (
    validate_read_only_cypher,
)

class Neo4jConnection:
    """Manages the Neo4j driver and connectivity checks."""

    def __init__(self) -> None:
        settings = get_settings()

        self._driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(
                settings.neo4j_username,
                settings.neo4j_password,
            ),
        )

        self._database = settings.neo4j_database

    @property
    def database(self) -> str:
        """Return the configured Neo4j database name."""
        return self._database

    def verify_connectivity(self) -> None:
        """Verify that the Neo4j server is reachable."""
        self._driver.verify_connectivity()

    def execute_read(
        self,
        query: str,
        parameters: dict | None = None,
    ):
        """Execute a validated read-only query and return its records."""

        validation = validate_read_only_cypher(query)

        if not validation["valid"]:
            errors = "; ".join(validation["errors"])

            raise ValueError(
                f"Cypher read query rejected: {errors}"
            )

        with self._driver.session(
            database=self._database
        ) as session:
            result = session.run(
                query,
                parameters or {},
            )

            return result.data()

    
# Change Start
    def execute_write(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """Execute a write query and return its records."""

        with self._driver.session(
            database=self._database
        ) as session:
            result = session.run(
                query,
                parameters or {},
            )
            return result.data()
# Change End

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        """Provide one explicit transaction for a multi-step write operation."""
        with self._driver.session(database=self._database) as session:
            transaction = session.begin_transaction()
            try:
                yield transaction
                transaction.commit()
            except Exception:
                transaction.rollback()
                raise
            finally:
                transaction.close()

    def close(self) -> None:
        """Close the Neo4j driver."""
        self._driver.close()


# Change End