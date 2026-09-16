import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import omarunctl  # noqa: E402
from storage import LOG_RESPONSE_BYTES  # noqa: E402


class UnitFileSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.unit_dir = Path(self.tmp.name) / "systemd" / "user"
        self.unit_dir.mkdir(parents=True, mode=0o700)
        self.task = {
            "id": "task-security-test",
            "name": "Security test",
            "command": "/usr/bin/true",
            "arguments": "",
            "workingDirectory": "",
            "timeoutSeconds": 0,
            "env": {},
            "schedule": {"enabled": False},
        }
        self.path_patch = mock.patch.object(
            omarunctl, "SYSTEMD_USER_DIR", self.unit_dir
        )
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.tmp.cleanup()

    def open_directory(self):
        return os.open(self.unit_dir, os.O_RDONLY | os.O_DIRECTORY)

    def test_generated_service_uses_owned_marker_and_closed_runtime(self):
        directory_fd = self.open_directory()
        try:
            omarunctl._write_service(self.task, directory_fd)
        finally:
            os.close(directory_fd)

        content = (self.unit_dir / "omarun-task-security-test.service").read_text()
        self.assertTrue(content.startswith("# Managed-By=io.github.za512.omarun"))
        self.assertIn("ExecStart=/usr/bin/env -i ", content)
        self.assertIn(" /usr/bin/python3 -E -s -X utf8 ", content)
        self.assertNotIn("/usr/bin/env python3", content)

    def test_symlink_collision_is_refused_without_touching_target(self):
        outside = Path(self.tmp.name) / "outside.service"
        outside.write_text("do not replace")
        unit = self.unit_dir / "omarun-task-security-test.service"
        unit.symlink_to(outside)

        directory_fd = self.open_directory()
        try:
            with self.assertRaisesRegex(omarunctl.OmaRunError, "symlink collision"):
                omarunctl._write_service(self.task, directory_fd)
        finally:
            os.close(directory_fd)

        self.assertEqual(outside.read_text(), "do not replace")
        self.assertTrue(unit.is_symlink())

    def test_foreign_regular_collision_is_refused(self):
        unit = self.unit_dir / "omarun-task-security-test.service"
        unit.write_text("[Unit]\nDescription=Foreign\n")

        directory_fd = self.open_directory()
        try:
            with self.assertRaisesRegex(omarunctl.OmaRunError, "foreign unit collision"):
                omarunctl._write_service(self.task, directory_fd)
        finally:
            os.close(directory_fd)

        self.assertEqual(unit.read_text(), "[Unit]\nDescription=Foreign\n")

    def test_fifo_collision_is_refused_without_blocking(self):
        unit = self.unit_dir / "omarun-task-security-test.service"
        os.mkfifo(unit)

        directory_fd = self.open_directory()
        try:
            with self.assertRaisesRegex(omarunctl.OmaRunError, "unowned unit collision"):
                omarunctl._write_service(self.task, directory_fd)
        finally:
            os.close(directory_fd)

        self.assertTrue(stat.S_ISFIFO(unit.lstat().st_mode))

    def test_exact_legacy_service_is_migrated(self):
        unit = self.unit_dir / "omarun-task-security-test.service"
        unit.write_text(omarunctl._legacy_service_content(self.task))

        directory_fd = self.open_directory()
        try:
            omarunctl._write_service(
                self.task, directory_fd, legacy_task=self.task
            )
        finally:
            os.close(directory_fd)

        self.assertTrue(unit.read_text().startswith("# Managed-By=io.github.za512.omarun"))

    def test_delete_preflights_before_systemctl(self):
        unit = self.unit_dir / "omarun-task-security-test.service"
        unit.write_text("[Unit]\nDescription=Foreign\n")

        with mock.patch.object(omarunctl, "_run_systemctl") as systemctl:
            with self.assertRaisesRegex(omarunctl.OmaRunError, "foreign unit collision"):
                omarunctl._remove_systemd_files(self.task)

        systemctl.assert_not_called()
        self.assertTrue(unit.exists())

    def test_update_race_restores_foreign_replacement(self):
        unit = self.unit_dir / "omarun-task-security-test.service"
        owned_aside = self.unit_dir / "owned-aside.service"
        directory_fd = self.open_directory()
        try:
            omarunctl._write_service(self.task, directory_fd)
            original_renameat2 = omarunctl._renameat2
            injected = False

            def raced_renameat2(fd, source, destination, flags):
                nonlocal injected
                if not injected and flags == omarunctl.RENAME_EXCHANGE:
                    injected = True
                    os.rename(
                        destination,
                        owned_aside.name,
                        src_dir_fd=fd,
                        dst_dir_fd=fd,
                    )
                    foreign_fd = os.open(
                        destination,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=fd,
                    )
                    with os.fdopen(foreign_fd, "wb") as foreign:
                        foreign.write(b"foreign replacement")
                return original_renameat2(fd, source, destination, flags)

            changed = {**self.task, "name": "Changed"}
            with mock.patch.object(omarunctl, "_renameat2", raced_renameat2):
                with self.assertRaisesRegex(omarunctl.OmaRunError, "changed during update"):
                    omarunctl._write_service(changed, directory_fd)
        finally:
            os.close(directory_fd)

        self.assertEqual(unit.read_bytes(), b"foreign replacement")
        self.assertTrue(owned_aside.read_text().startswith("# Managed-By="))

    def test_removal_race_restores_foreign_replacement(self):
        unit = self.unit_dir / "omarun-task-security-test.service"
        owned_aside = self.unit_dir / "owned-aside.service"
        directory_fd = self.open_directory()
        try:
            omarunctl._write_service(self.task, directory_fd)
            original_renameat2 = omarunctl._renameat2
            injected = False

            def raced_renameat2(fd, source, destination, flags):
                nonlocal injected
                if not injected and flags == omarunctl.RENAME_NOREPLACE:
                    injected = True
                    os.rename(
                        source,
                        owned_aside.name,
                        src_dir_fd=fd,
                        dst_dir_fd=fd,
                    )
                    foreign_fd = os.open(
                        source,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=fd,
                    )
                    with os.fdopen(foreign_fd, "wb") as foreign:
                        foreign.write(b"foreign replacement")
                return original_renameat2(fd, source, destination, flags)

            with mock.patch.object(omarunctl, "_renameat2", raced_renameat2):
                with self.assertRaisesRegex(omarunctl.OmaRunError, "changed during removal"):
                    omarunctl._remove_unit_at(directory_fd, self.task, "service")
        finally:
            os.close(directory_fd)

        self.assertEqual(unit.read_bytes(), b"foreign replacement")
        self.assertTrue(owned_aside.read_text().startswith("# Managed-By="))


class ResponseBoundTests(unittest.TestCase):
    def test_encoded_log_response_has_a_strict_ceiling(self):
        payload = {
            "id": "task-security-test",
            "running": False,
            "source": "last.log",
            "text": "\x00" * LOG_RESPONSE_BYTES,
            "truncated": False,
        }

        rendered = omarunctl._bounded_log_response(payload)
        decoded = json.loads(rendered)

        self.assertLessEqual(len(rendered), LOG_RESPONSE_BYTES)
        self.assertTrue(decoded["truncated"])
        self.assertTrue(decoded["text"].startswith("[... log response truncated"))

    def test_invalid_utf8_log_is_displayed_with_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            (state_dir / "last.log").write_bytes(b"valid\xfftail")
            with mock.patch.object(omarunctl, "task_state_dir", return_value=state_dir):
                payload = omarunctl._read_log(
                    "task-security-test", prefer_running=False
                )

        self.assertEqual(payload["text"], "valid\ufffdtail")


class InterpreterIsolationTests(unittest.TestCase):
    def test_hostile_path_and_pythonpath_do_not_run_before_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            hostile = Path(tmp) / "hostile"
            fake_bin = Path(tmp) / "bin"
            home.mkdir()
            hostile.mkdir()
            fake_bin.mkdir()
            sentinel = Path(tmp) / "executed"
            (hostile / "sitecustomize.py").write_text(
                f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('sitecustomize')\n"
            )
            fake_python = fake_bin / "python3"
            fake_python.write_text(f"#!/bin/sh\nprintf fake > {sentinel}\n")
            fake_python.chmod(0o755)
            environment = {
                "HOME": str(home),
                "PATH": str(fake_bin),
                "PYTHONPATH": str(hostile),
                "PYTHONHOME": str(hostile),
            }

            result = subprocess.run(
                [
                    "/usr/bin/python3",
                    "-E",
                    "-s",
                    "-X",
                    "utf8",
                    str(BACKEND / "omarunctl.py"),
                    "list",
                ],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            sentinel_exists = sentinel.exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel_exists)
        self.assertEqual(json.loads(result.stdout), {"tasks": []})


class QmlLauncherSecurityTests(unittest.TestCase):
    def test_qml_helpers_use_absolute_python_and_cleared_environments(self):
        for filename, process_count in (("Panel.qml", 7), ("BarWidget.qml", 1)):
            text = (ROOT / filename).read_text()
            with self.subTest(filename=filename):
                self.assertIn('"/usr/bin/python3", "-E", "-s"', text)
                self.assertNotIn('["python3"', text)
                self.assertEqual(text.count("clearEnvironment: true"), process_count)
                self.assertEqual(text.count("environment: ({})"), process_count)


if __name__ == "__main__":
    unittest.main()
