import logging
import os
import subprocess
import sys
from unittest import mock

from django.db.utils import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings

from core.alerts import COOLDOWN, TelegramHandler

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class HealthzTests(TestCase):
    def test_ok_when_database_answers(self):
        res = self.client.get("/healthz/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_503_when_database_is_down(self):
        with mock.patch("core.views.connection.cursor", side_effect=OperationalError("down")):
            res = self.client.get("/healthz/")
        self.assertEqual(res.status_code, 503)


def record(msg="boom"):
    return logging.LogRecord("django.request", logging.ERROR, __file__, 1, msg, None, None)


@override_settings(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="c")
class TelegramHandlerTests(SimpleTestCase):
    def setUp(self):
        self.now = 1000.0
        self.handler = TelegramHandler(clock=lambda: self.now)

    def test_sends_an_error(self):
        with mock.patch("core.alerts.requests.post") as post:
            self.handler.emit(record())
        post.assert_called_once()
        self.assertIn("boom", post.call_args.kwargs["data"]["text"])

    def test_same_error_is_sent_once_per_cooldown(self):
        with mock.patch("core.alerts.requests.post") as post:
            for _ in range(50):
                self.handler.emit(record())
            self.now += COOLDOWN + 1
            self.handler.emit(record())
        self.assertEqual(post.call_count, 2)

    def test_a_failing_alert_never_raises(self):
        self.handler.handleError = mock.Mock()
        with mock.patch("core.alerts.requests.post", side_effect=OSError("no network")):
            self.handler.emit(record())  # must not raise
        self.handler.handleError.assert_called_once()

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_does_nothing_when_not_configured(self):
        with mock.patch("core.alerts.requests.post") as post:
            self.handler.emit(record())
        post.assert_not_called()


class ProductionSettingsTests(SimpleTestCase):
    def run_manage(self, *args, **env):
        full_env = {**os.environ, **env}
        return subprocess.run(
            [sys.executable, "manage.py", *args], cwd=BASE, env=full_env, capture_output=True, text=True
        )

    def test_deploy_checks_pass_with_production_settings(self):
        res = self.run_manage(
            "check", "--deploy", "--fail-level", "WARNING",
            DEBUG="0", SECRET_KEY="x" * 60 + "production-like-key", ALLOWED_HOSTS="example.com",
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_refuses_to_start_without_a_secret_key(self):
        res = self.run_manage("check", DEBUG="0", SECRET_KEY="")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("SECRET_KEY is required", res.stderr)
