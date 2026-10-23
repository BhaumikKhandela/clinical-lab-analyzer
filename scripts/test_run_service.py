"""Offline checks for cloud database URL conversion."""

import unittest
from urllib.parse import parse_qs, urlsplit

from run_service import database_environment


class DatabaseEnvironmentTests(unittest.TestCase):
    def test_neon_ssl_and_encoded_credentials(self):
        env = database_environment(
            "postgresql://user%40team:p%40ss%3Aword@db.example/neondb"
            "?sslmode=require&channel_binding=require"
        )
        self.assertEqual(env["SPRING_DATASOURCE_USERNAME"], "user@team")
        self.assertEqual(env["SPRING_DATASOURCE_PASSWORD"], "p@ss:word")
        jdbc = env["SPRING_DATASOURCE_URL"]
        self.assertNotIn("p@ss", jdbc)
        self.assertEqual(parse_qs(urlsplit(jdbc.removeprefix("jdbc:")).query),
                         {"sslmode": ["require"], "channelBinding": ["require"]})

    def test_port_and_ipv6(self):
        env = database_environment("postgres://u:p@[::1]:5433/lab-auth")
        self.assertEqual(env["SPRING_DATASOURCE_URL"], "jdbc:postgresql://[::1]:5433/lab-auth")

    def test_invalid_urls(self):
        for value in ("", "https://example.com/db", "postgresql://example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                database_environment(value)


if __name__ == "__main__":
    unittest.main()
