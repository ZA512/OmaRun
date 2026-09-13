import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import omarunctl  # noqa: E402


class ScheduleTimerTests(unittest.TestCase):
    def test_interval_schedules_have_initial_and_recurring_triggers(self):
        cases = {
            "every-minutes": (15, "15min"),
            "every-hours": (6, "6h"),
            "every-days": (2, "2d"),
        }

        for mode, (interval, expected_interval) in cases.items():
            with self.subTest(mode=mode):
                lines = omarunctl._schedule_to_timer_lines(
                    {"mode": mode, "interval": interval}
                )
                self.assertEqual(
                    lines,
                    [
                        f"OnActiveSec={expected_interval}",
                        f"OnUnitActiveSec={expected_interval}",
                    ],
                )

    def test_calendar_schedules_are_unchanged(self):
        self.assertEqual(
            omarunctl._schedule_to_timer_lines(
                {"mode": "daily-at", "time": "03:15"}
            ),
            ["OnCalendar=*-*-* 03:15:00"],
        )

    def test_writing_a_timer_restarts_it_after_enabling(self):
        task_id = "task-test-schedule"
        task = {
            "id": task_id,
            "name": "Test schedule",
            "schedule": {
                "enabled": True,
                "mode": "every-hours",
                "interval": 6,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            timer_path = Path(tmp) / f"omarun-{task_id}.timer"
            with (
                mock.patch.object(omarunctl, "_timer_path", return_value=timer_path),
                mock.patch.object(omarunctl, "_daemon_reload") as daemon_reload,
                mock.patch.object(omarunctl, "_run_systemctl") as run_systemctl,
            ):
                omarunctl._write_or_remove_timer(task)
                timer_text = timer_path.read_text()

        self.assertIn("OnActiveSec=6h", timer_text)
        self.assertIn("OnUnitActiveSec=6h", timer_text)
        daemon_reload.assert_called_once_with()
        self.assertEqual(
            run_systemctl.call_args_list,
            [
                mock.call(["enable", f"omarun-{task_id}.timer"]),
                mock.call(["restart", f"omarun-{task_id}.timer"]),
            ],
        )


if __name__ == "__main__":
    unittest.main()
