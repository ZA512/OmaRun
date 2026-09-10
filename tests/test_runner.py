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


if __name__ == "__main__":
    unittest.main()
