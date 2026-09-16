import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "backend" / "runner.py"
sys.path.insert(0, str(ROOT / "backend"))

from storage import LOG_STORAGE_BYTES  # noqa: E402


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.task_id = "task-test-runner"
        self.env = os.environ | {"HOME": str(self.home)}

    def tearDown(self):
        self.tmp.cleanup()

    def write_task(self, arguments: str):
        config = self.home / ".config" / "omarun"
        config.mkdir(parents=True)
        (config / "tasks.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": self.task_id,
                            "name": "Test",
                            "command": sys.executable,
                            "arguments": arguments,
                            "workingDirectory": "",
                            "timeoutSeconds": 0,
                            "env": {},
                            "schedule": {"enabled": False},
                        }
                    ]
                }
            )
        )

    def status_path(self) -> Path:
        return self.home / ".local" / "state" / "omarun" / "tasks" / self.task_id / "status.json"

    def test_success_records_status_and_log(self):
        self.write_task('-c "print(\'hello from task\')"')
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--task-id", self.task_id],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(self.status_path().read_text())
        self.assertEqual(status["status"], "success")
        log = self.status_path().with_name("last.log").read_text()
        self.assertIn("hello from task", log)

    def test_sigterm_records_stopped_status(self):
        self.write_task('-c "import time; time.sleep(30)"')
        process = subprocess.Popen(
            [sys.executable, str(RUNNER), "--task-id", self.task_id],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        while not self.status_path().parent.joinpath("current.log").exists():
            self.assertLess(time.monotonic(), deadline, "runner did not start")
            time.sleep(0.05)
        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=15)
        self.assertEqual(process.returncode, 0)
        status = json.loads(self.status_path().read_text())
        self.assertEqual(status["status"], "stopped")

    def test_launch_failure_records_status_and_log(self):
        self.write_task("")
        tasks_path = self.home / ".config" / "omarun" / "tasks.json"
        data = json.loads(tasks_path.read_text())
        data["tasks"][0]["command"] = "/definitely/missing/omarun-command"
        tasks_path.write_text(json.dumps(data))

        result = subprocess.run(
            [sys.executable, str(RUNNER), "--task-id", self.task_id],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        status = json.loads(self.status_path().read_text())
        self.assertEqual(status["status"], "failed")
        self.assertIn("Failed to start", status["message"])
        log = self.status_path().with_name("last.log").read_text()
        self.assertIn("/definitely/missing/omarun-command", log)
        self.assertIn("[ERROR]", log)

    def test_large_output_keeps_only_a_bounded_recent_window(self):
        byte_count = LOG_STORAGE_BYTES + 1024 * 1024
        self.write_task(
            f'-c "import sys; sys.stdout.buffer.write(b\\\"x\\\" * {byte_count})"'
        )

        result = subprocess.run(
            [sys.executable, str(RUNNER), "--task-id", self.task_id],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        log_path = self.status_path().with_name("last.log")
        self.assertLessEqual(log_path.stat().st_size, LOG_STORAGE_BYTES)
        with log_path.open("rb") as log:
            beginning = log.read(64)
            log.seek(-64, os.SEEK_END)
            ending = log.read()
        self.assertIn(b"earlier output omitted", beginning)
        self.assertEqual(ending, b"x" * 64)


if __name__ == "__main__":
    unittest.main()
