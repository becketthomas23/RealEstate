import unittest

from backend.persistence.database import _escape_alembic_config_value, _normalize_database_url


class DatabaseUrlTests(unittest.TestCase):
    def test_supabase_session_pooler_url_uses_psycopg_and_tls(self) -> None:
        url = "postgresql://postgres.project:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

        self.assertEqual(
            _normalize_database_url(url),
            "postgresql+psycopg://postgres.project:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require",
        )

    def test_url_encoded_password_is_escaped_for_alembic_config(self) -> None:
        url = "postgresql+psycopg://postgres:%24password@example.com/postgres"

        self.assertEqual(
            _escape_alembic_config_value(url),
            "postgresql+psycopg://postgres:%%24password@example.com/postgres",
        )
