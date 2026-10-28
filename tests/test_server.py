import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from flask.cli import load_dotenv
from sqlalchemy.exc import OperationalError

import server


class StarterTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.client = server.app.test_client()
        server.get_engine.cache_clear()

    def tearDown(self):
        server.get_engine.cache_clear()
        self.environment.stop()

    def database(self, results=()):
        os.environ.update(DB_USER="test_user", DB_PASSWORD="test-only:@/?")
        engine = MagicMock()
        conn = engine.connect.return_value
        conn.execute.return_value.scalar_one.side_effect = list(results)
        return engine, conn

    def test_local_settings_load_into_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "local-settings.txt"
            settings.write_text("DB_USER=test_user\nDB_PASSWORD='test-only:#@/?'\n")
            self.assertTrue(load_dotenv(path=settings, load_defaults=False))
        self.assertEqual(os.environ["DB_USER"], "test_user")
        self.assertEqual(os.environ["DB_PASSWORD"], "test-only:#@/?")
        with patch("server.create_engine") as create_engine:
            server.get_engine()
        self.assertEqual(create_engine.call_args.args[0].password, "test-only:#@/?")

    def test_existing_environment_takes_precedence_over_local_settings(self):
        os.environ["DB_PASSWORD"] = "injected-test-only-value"
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "local-settings.txt"
            settings.write_text("DB_PASSWORD=file-test-only-value\n")
            load_dotenv(path=settings, load_defaults=False)
        self.assertEqual(os.environ["DB_PASSWORD"], "injected-test-only-value")

    def test_development_server_requests_dotenv_loading(self):
        with patch("flask.cli.load_dotenv") as loader:
            with patch("flask.cli.show_server_banner"):
                with patch("werkzeug.serving.run_simple") as run_simple:
                    server.app.run(host="127.0.0.1", port=8111)
        loader.assert_called_once()
        run_simple.assert_called_once()

    def test_home_renders_before_database_configuration(self):
        with patch("server.get_engine") as get_engine:
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Some famous Computer Scientists", response.data)
        self.assertIn(b"not configured", response.data)
        self.assertNotIn(b"Initialize example table", response.data)
        get_engine.assert_not_called()

    def test_other_page_and_static_asset_do_not_connect(self):
        with patch("server.get_engine") as get_engine:
            self.assertEqual(self.client.get("/another").status_code, 200)
            response = self.client.get("/static/style.css")
            self.assertEqual(response.status_code, 200)
            response.close()
        get_engine.assert_not_called()

    def test_missing_configuration_database_check_is_503(self):
        response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {"database": "unavailable"})

    def test_database_check_uses_bound_parameter_and_effective_schema(self):
        engine, conn = self.database([1, True, False])
        with patch("server.get_engine", return_value=engine):
            response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["select_1"], 1)
        self.assertTrue(response.json["current_schema_accessible"])
        self.assertFalse(response.json["demo_table_exists"])
        query, params = conn.execute.call_args_list[0].args
        self.assertEqual(str(query), "SELECT :value")
        self.assertEqual(params, {"value": 1})
        self.assertIn("current_schema()", str(conn.execute.call_args_list[1].args[0]))
        conn.close.assert_called_once()

    def test_schema_is_bound_and_quoted(self):
        engine, conn = self.database([1, True, False])
        os.environ["DB_SCHEMA"] = 'assigned"schema'
        with patch("server.get_engine", return_value=engine):
            response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 200)
        query, params = conn.execute.call_args_list[0].args
        self.assertIn("quote_ident(:schema)", str(query))
        self.assertEqual(params, {"schema": 'assigned"schema'})
        conn.commit.assert_called_once()

    def test_initialization_without_database_is_503(self):
        response = self.client.post("/initialize")
        self.assertEqual(response.status_code, 503)

    def test_initialization_requires_a_post_request(self):
        self.assertEqual(self.client.get("/initialize").status_code, 405)

    def test_initialization_is_explicit_and_commits(self):
        engine, conn = self.database()
        with patch("server.get_engine", return_value=engine):
            response = self.client.post("/initialize")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(conn.execute.call_count, 2)
        statements = [str(call.args[0]) for call in conn.execute.call_args_list]
        self.assertIn("CREATE TABLE IF NOT EXISTS test", statements[0])
        self.assertIn("WHERE NOT EXISTS", statements[1])
        self.assertFalse(any("CREATE SCHEMA" in s for s in statements))
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_home_does_not_implicitly_create_table(self):
        engine, conn = self.database([False])
        with patch("server.get_engine", return_value=engine):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Initialize example table", response.data)
        self.assertEqual(conn.execute.call_count, 1)
        conn.commit.assert_not_called()

    def test_original_names_template_escapes_html(self):
        engine, conn = self.database([True])
        cursor = MagicMock()
        cursor.__iter__.return_value = iter([("<script>example</script>",)])
        conn.execute.side_effect = [MagicMock(scalar_one=lambda: True), cursor]
        with patch("server.get_engine", return_value=engine):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertNotIn(b"<script>", response.data)
        self.assertNotIn(b"Initialize example table", response.data)
        self.assertIn(b'action="/add"', response.data)
        cursor.close.assert_called_once()

    def test_add_binds_user_input_and_commits(self):
        engine, conn = self.database()
        name = "Robert'); DROP TABLE test; --"
        with patch("server.get_engine", return_value=engine):
            response = self.client.post("/add", data={"name": name})
        self.assertEqual(response.status_code, 302)
        query, params = conn.execute.call_args.args
        self.assertEqual(str(query), "INSERT INTO test(name) VALUES (:name)")
        self.assertEqual(params, {"name": name})
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_add_rejects_empty_and_long_names(self):
        for name in ("", "   ", "a" * 101):
            with self.subTest(name_length=len(name)):
                self.assertEqual(self.client.post("/add", data={"name": name}).status_code, 400)

    def test_connection_failure_is_safe(self):
        engine, conn = self.database()
        engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("private-test-only-detail"))
        with patch("server.get_engine", return_value=engine):
            with self.assertLogs(server.app.logger, level="WARNING") as logs:
                response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {"database": "unavailable"})
        self.assertNotIn("private-test-only-detail", "\n".join(logs.output))

    def test_query_failure_rolls_back_and_closes(self):
        engine, conn = self.database()
        conn.execute.side_effect = OperationalError("SELECT 1", {}, Exception("private-test-only-detail"))
        with patch("server.get_engine", return_value=engine):
            with self.assertLogs(server.app.logger, level="WARNING") as logs:
                response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 503)
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()
        self.assertNotIn("private-test-only-detail", "\n".join(logs.output))

    def test_login_remains_only_an_error_example(self):
        self.assertEqual(self.client.get("/login").status_code, 401)

    def test_url_and_pool_configuration(self):
        self.database()
        with patch("server.create_engine") as create_engine:
            server.get_engine()
            server.get_engine()
        create_engine.assert_called_once()
        args, options = create_engine.call_args
        self.assertEqual(args[0].password, "test-only:@/?")
        self.assertEqual(args[0].host, "127.0.0.1")
        self.assertEqual(args[0].port, 5454)
        self.assertEqual(options["pool_size"], 1)
        self.assertEqual(options["max_overflow"], 0)
        self.assertTrue(options["pool_pre_ping"])


if __name__ == "__main__":
    unittest.main()
