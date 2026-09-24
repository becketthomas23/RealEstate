import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import inspect

from backend.persistence import Database


class MigrationTests(unittest.TestCase):
    def test_initial_migration_creates_the_persistence_schema(self) -> None:
        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "migration-test.db"
            database = Database(f"sqlite:///{database_path.as_posix()}")
            try:
                database.upgrade_schema()
                table_names = set(inspect(database.engine).get_table_names())
            finally:
                database.dispose()

        self.assertTrue(
            {
                "alembic_version",
                "deals",
                "assumption_sets",
                "calculation_runs",
                "calculation_results",
            }.issubset(table_names)
        )
