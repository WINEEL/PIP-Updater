import io
import os
import sys
import tempfile
import unittest
import contextlib
import subprocess

from pathlib import Path
from unittest import mock

import main
from application.filterpip import filterpip
import cli.cli as cli_wrapper


def completed(stdout=""):
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


class PipUpdateTests(unittest.TestCase):
    def test_successful_normal_workflow_orchestration(self):
        results = [completed(), completed("alpha==1.0\nbeta==2.0\n"), completed()]

        with mock.patch("main.subprocess.run", side_effect=results) as run:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main.PipUpdate(python_cmd="python path").run()

        self.assertEqual(run.call_count, 3)
        self.assertEqual(
            run.call_args_list[0].args[0],
            ["python path", "-m", "pip", "install", "--upgrade", "pip"],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["python path", "-m", "pip", "freeze"],
        )
        self.assertEqual(
            run.call_args_list[2].args[0][0:6],
            ["python path", "-m", "pip", "install", "--upgrade", "-r"],
        )
        self.assertIn("Successfully updated", output.getvalue())

    def test_dry_run_only_discovers_packages(self):
        with mock.patch(
            "main.subprocess.run", return_value=completed("alpha==1.0\n")
        ) as run:
            main.PipUpdate(dry_run=True, python_cmd="python").run()

        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0], ["python", "-m", "pip", "freeze"]
        )

    def test_dry_run_does_not_touch_historical_data_directory(self):
        with tempfile.TemporaryDirectory() as working_dir:
            historical_dir = Path(working_dir) / "datap_"
            historical_dir.mkdir()
            marker = historical_dir / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            original_dir = Path.cwd()
            try:
                os.chdir(working_dir)
                with mock.patch(
                    "main.subprocess.run", return_value=completed("alpha==1.0\n")
                ), mock.patch("main.tempfile.TemporaryDirectory") as temp_directory:
                    main.PipUpdate(dry_run=True, python_cmd="python").run()
            finally:
                os.chdir(original_dir)

            temp_directory.assert_not_called()
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_pip_upgrade_failure_prevents_success(self):
        error = subprocess.CalledProcessError(1, ["python"], stderr="pip failed")
        output = io.StringIO()

        with mock.patch("main.subprocess.run", side_effect=error):
            with contextlib.redirect_stdout(output):
                with self.assertRaises(main.PipUpdateError):
                    main.PipUpdate(python_cmd="python").run()

        self.assertNotIn("Successfully", output.getvalue())

    def test_package_upgrade_failure_prevents_success(self):
        results = [
            completed(),
            completed("alpha==1.0\n"),
            subprocess.CalledProcessError(1, ["python"], stderr="package failed"),
        ]
        output = io.StringIO()

        with mock.patch("main.subprocess.run", side_effect=results):
            with contextlib.redirect_stdout(output):
                with self.assertRaises(main.PipUpdateError):
                    main.PipUpdate(python_cmd="python").run()

        self.assertNotIn("Successfully", output.getvalue())

    def test_subprocess_uses_argument_lists_without_a_shell(self):
        with mock.patch("main.subprocess.run", return_value=completed()) as run:
            main.PipUpdate(python_cmd="python path").run_command(
                ["python path", "-m", "pip", "freeze"]
            )

        self.assertIsInstance(run.call_args.args[0], list)
        self.assertIs(run.call_args.kwargs["shell"], False)

    def test_filterpip_parses_ordinary_pinned_packages(self):
        self.assertEqual(
            filterpip("alpha==1.0\nbeta-package===2.0\n"),
            ["alpha", "beta-package"],
        )

    def test_filterpip_skips_direct_and_editable_references(self):
        sensitive_marker = "SUPER_SECRET_TOKEN_123"
        freeze_output = (
            "alpha==1.0\n"
            f"direct @ https://example.invalid/direct.whl?token={sensitive_marker}\n"
            "-e git+https://example.invalid/repo.git#egg=editable\n"
        )
        output = io.StringIO()
        warnings = io.StringIO()

        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(warnings):
            packages = filterpip(freeze_output)

        self.assertEqual(packages, ["alpha"])
        requirements_output = "\n".join(packages)
        self.assertNotIn(sensitive_marker, requirements_output)
        self.assertNotIn(sensitive_marker, output.getvalue())
        self.assertNotIn(sensitive_marker, warnings.getvalue())
        self.assertNotIn("https://", warnings.getvalue())
        self.assertEqual(
            warnings.getvalue().count("skipping an unsupported package entry"), 2
        )

    def test_temporary_resources_are_cleaned_after_upgrade_failure(self):
        requirements_paths = []

        def run_command(command, **kwargs):
            if command[-2:-1] == ["-r"]:
                requirements_path = Path(command[-1])
                self.assertTrue(requirements_path.exists())
                requirements_paths.append(requirements_path)
                raise subprocess.CalledProcessError(1, command, stderr="failed")
            if command[-2:] == ["pip", "freeze"]:
                return completed("alpha==1.0\n")
            return completed()

        with mock.patch("main.subprocess.run", side_effect=run_command):
            with self.assertRaises(main.PipUpdateError):
                main.PipUpdate(python_cmd="python").run()

        self.assertEqual(len(requirements_paths), 1)
        self.assertFalse(requirements_paths[0].exists())
        self.assertFalse(requirements_paths[0].parent.exists())

    def test_frozen_executable_cannot_invoke_itself_as_python(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            with mock.patch("main.subprocess.run") as run:
                with self.assertRaisesRegex(
                    main.PipUpdateError, "cannot safely determine"
                ):
                    main.PipUpdate()

        run.assert_not_called()

    def test_cli_wrapper_delegates_to_application_main(self):
        with mock.patch("cli.cli.application_main", return_value=7) as application_main:
            self.assertEqual(cli_wrapper.cli(), 7)

        application_main.assert_called_once_with()

    def test_main_returns_nonzero_when_workflow_fails(self):
        error_output = io.StringIO()
        with mock.patch("main.configure_logging"), mock.patch(
            "main.logging.error"
        ), mock.patch(
            "main.PipUpdate.run", side_effect=main.PipUpdateError("failed")
        ), contextlib.redirect_stderr(error_output):
            exit_status = main.main([])

        self.assertEqual(exit_status, 1)
        self.assertIn("Error: failed", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
