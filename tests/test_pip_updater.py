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


def validated_updater(dry_run=False, python_cmd="python path"):
    updater = main.PipUpdate(dry_run=dry_run, python_cmd=python_cmd)
    updater.python_validated = True
    return updater


def command_list(run_mock):
    return [call.args[0] for call in run_mock.call_args_list]


class PipUpdateTests(unittest.TestCase):
    def test_successful_normal_workflow_orchestration(self):
        results = [completed(), completed("alpha==1.0\nbeta==2.0\n"), completed()]

        with mock.patch("main.subprocess.run", side_effect=results) as run:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                updater = validated_updater()
                updater.run()

        self.assertEqual(run.call_count, 3)
        self.assertEqual(
            run.call_args_list[0].args[0],
            [updater.python_cmd, "-m", "pip", "install", "--upgrade", "pip"],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            [updater.python_cmd, "-m", "pip", "freeze"],
        )
        self.assertEqual(
            run.call_args_list[2].args[0][0:6],
            [updater.python_cmd, "-m", "pip", "install", "--upgrade", "-r"],
        )
        self.assertIn("Successfully updated", output.getvalue())

    def test_source_dry_run_only_discovers_packages(self):
        with mock.patch(
            "main.subprocess.run", return_value=completed("alpha==1.0\n")
        ) as run:
            main.PipUpdate(dry_run=True).run()

        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0], [sys.executable, "-m", "pip", "freeze"]
        )
        self.assertNotIn("install", run.call_args.args[0])

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
                    main.PipUpdate(dry_run=True).run()
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
                    validated_updater().run()

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
                    validated_updater().run()

        self.assertNotIn("Successfully", output.getvalue())

    def test_subprocess_uses_argument_lists_without_a_shell(self):
        with mock.patch("main.subprocess.run", return_value=completed()) as run:
            updater = main.PipUpdate(python_cmd="python path")
            updater.run_command(
                ["python path", "-m", "pip", "freeze"]
            )

        self.assertIsInstance(run.call_args.args[0], list)
        self.assertIs(run.call_args.kwargs["shell"], False)
        self.assertNotIn("env", run.call_args.kwargs)

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
                validated_updater().run()

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

    def test_source_without_python_defaults_to_sys_executable(self):
        updater = main.PipUpdate()

        self.assertEqual(updater.python_cmd, sys.executable)
        self.assertTrue(updater.python_validated)

    def test_source_accepts_valid_explicit_python(self):
        results = [
            completed(main.PYTHON_IDENTITY_MARKER + "\n"),
            completed("pip 25.0"),
            completed("alpha==1.0\n"),
        ]

        with mock.patch("main.subprocess.run", side_effect=results) as run:
            updater = main.PipUpdate(dry_run=True, python_cmd="selected-python")
            updater.run()

        commands = command_list(run)
        self.assertEqual(commands[0][0], updater.python_cmd)
        self.assertEqual(commands[1], [updater.python_cmd, "-m", "pip", "--version"])
        self.assertEqual(commands[2], [updater.python_cmd, "-m", "pip", "freeze"])

    def test_frozen_with_valid_explicit_python_proceeds(self):
        results = [
            completed(main.PYTHON_IDENTITY_MARKER + "\n"),
            completed("pip 25.0"),
            completed(),
            completed(""),
        ]

        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "executable", "/app/PIP-Updater"
        ), mock.patch("main.subprocess.run", side_effect=results) as run:
            updater = main.PipUpdate(python_cmd="/target/python")
            updater.run()

        self.assertTrue(updater.python_validated)
        self.assertEqual(run.call_count, 4)
        for command in command_list(run):
            self.assertEqual(command[0], updater.python_cmd)

    def test_frozen_sys_executable_never_becomes_pip_target(self):
        results = [
            completed(main.PYTHON_IDENTITY_MARKER + "\n"),
            completed("pip 25.0"),
            completed(""),
        ]

        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "executable", "/app/PIP-Updater"
        ), mock.patch("main.subprocess.run", side_effect=results) as run:
            updater = main.PipUpdate(dry_run=True, python_cmd="/target/python")
            updater.run()

        pip_commands = [command for command in command_list(run) if "-m" in command]
        self.assertTrue(pip_commands)
        self.assertTrue(all(command[0] != "/app/PIP-Updater" for command in pip_commands))

    def test_explicit_target_equal_to_frozen_executable_is_rejected(self):
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "executable", "/app/PIP-Updater"
        ), mock.patch("main.subprocess.run") as run:
            with self.assertRaisesRegex(main.PipUpdateError, "PIP-Updater executable"):
                main.PipUpdate(python_cmd="/app/PIP-Updater").run()

        run.assert_not_called()

    def test_samefile_alias_of_frozen_executable_is_rejected(self):
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch(
            "main.os.path.samefile", return_value=True
        ), mock.patch("main.subprocess.run") as run:
            with self.assertRaisesRegex(main.PipUpdateError, "PIP-Updater executable"):
                main.PipUpdate(python_cmd="/alias/updater").run()

        run.assert_not_called()

    def test_copied_non_python_executable_never_reaches_pip(self):
        identity_failure = subprocess.CalledProcessError(
            2, ["copied-updater", "-I", "-c"], stderr="unrecognized arguments"
        )

        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "executable", "/app/PIP-Updater"
        ), mock.patch("main.subprocess.run", side_effect=identity_failure) as run:
            with self.assertRaisesRegex(main.PipUpdateError, "identity check"):
                main.PipUpdate(python_cmd="/copy/PIP-Updater").run()

        self.assertEqual(run.call_count, 1)
        self.assertNotIn("-m", run.call_args.args[0])

    def test_python_identity_marker_mismatch_stops_execution(self):
        with mock.patch(
            "main.subprocess.run", return_value=completed("not the marker\n")
        ) as run:
            with self.assertRaisesRegex(main.PipUpdateError, "did not identify"):
                main.PipUpdate(python_cmd="selected-python").run()

        self.assertEqual(run.call_count, 1)
        self.assertNotIn("-m", run.call_args.args[0])

    def test_pip_version_failure_stops_execution(self):
        pip_failure = subprocess.CalledProcessError(
            1, ["python", "-m", "pip", "--version"], stderr="No module named pip"
        )
        results = [completed(main.PYTHON_IDENTITY_MARKER + "\n"), pip_failure]

        with mock.patch("main.subprocess.run", side_effect=results) as run:
            with self.assertRaisesRegex(main.PipUpdateError, "working pip"):
                main.PipUpdate(python_cmd="selected-python").run()

        self.assertEqual(run.call_count, 2)
        self.assertEqual(command_list(run)[-1][-3:], ["-m", "pip", "--version"])
        self.assertFalse(any("install" in command for command in command_list(run)))

    def test_all_pip_commands_use_same_validated_interpreter(self):
        results = [
            completed(main.PYTHON_IDENTITY_MARKER + "\n"),
            completed("pip 25.0"),
            completed(),
            completed("alpha==1.0\n"),
            completed(),
        ]

        with mock.patch("main.subprocess.run", side_effect=results) as run:
            updater = main.PipUpdate(python_cmd="selected-python")
            updater.run()

        pip_commands = [command for command in command_list(run) if "pip" in command]
        self.assertEqual(len(pip_commands), 4)
        self.assertTrue(
            all(command[0] == updater.python_cmd for command in pip_commands)
        )

    def test_frozen_dry_run_validates_and_freezes_without_upgrade(self):
        results = [
            completed(main.PYTHON_IDENTITY_MARKER + "\n"),
            completed("pip 25.0"),
            completed("alpha==1.0\n"),
        ]

        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "executable", "/app/PIP-Updater"
        ), mock.patch("main.subprocess.run", side_effect=results) as run:
            updater = main.PipUpdate(dry_run=True, python_cmd="/target/python")
            updater.run()

        commands = command_list(run)
        self.assertEqual(commands[-1], [updater.python_cmd, "-m", "pip", "freeze"])
        self.assertFalse(any("install" in command for command in commands))

    def test_linux_frozen_environment_restores_original_library_path(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            updater = main.PipUpdate(python_cmd="/target/python")

        environment = {
            "LD_LIBRARY_PATH": "/bundle",
            "LD_LIBRARY_PATH_ORIG": "/system/libs",
            "KEEP": "value",
        }
        with mock.patch.object(sys, "platform", "linux"), mock.patch.dict(
            os.environ, environment, clear=True
        ):
            sanitized = updater._subprocess_environment()

        self.assertEqual(sanitized["LD_LIBRARY_PATH"], "/system/libs")
        self.assertEqual(sanitized["KEEP"], "value")

    def test_linux_frozen_environment_removes_added_library_path(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            updater = main.PipUpdate(python_cmd="/target/python")

        with mock.patch.object(sys, "platform", "linux"), mock.patch.dict(
            os.environ, {"LD_LIBRARY_PATH": "/bundle"}, clear=True
        ):
            sanitized = updater._subprocess_environment()

        self.assertNotIn("LD_LIBRARY_PATH", sanitized)

    def test_macos_removes_only_bundle_dyld_entries(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            updater = main.PipUpdate(python_cmd="/target/python")

        environment = {
            "DYLD_LIBRARY_PATH": os.pathsep.join(
                ["/system/libs", "/tmp/_MEI123", "/tmp/_MEI123/lib"]
            )
        }
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(
            sys, "_MEIPASS", "/tmp/_MEI123", create=True
        ), mock.patch.dict(os.environ, environment, clear=True):
            sanitized = updater._subprocess_environment()

        self.assertEqual(sanitized["DYLD_LIBRARY_PATH"], "/system/libs")

    def test_macos_leaves_uncontaminated_dyld_path_unchanged(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            updater = main.PipUpdate(python_cmd="/target/python")

        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(
            sys, "_MEIPASS", "/tmp/_MEI123", create=True
        ), mock.patch.dict(
            os.environ, {"DYLD_LIBRARY_PATH": "/system/libs"}, clear=True
        ):
            sanitized = updater._subprocess_environment()

        self.assertEqual(sanitized["DYLD_LIBRARY_PATH"], "/system/libs")

    def test_windows_dll_search_path_is_cleared_once_before_subprocess(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            updater = main.PipUpdate(python_cmd="/target/python")

        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(
            updater, "_clear_windows_dll_directory"
        ) as clear_dll_directory, mock.patch(
            "main.subprocess.run", return_value=completed()
        ) as run:
            updater.run_command([updater.python_cmd, "-c", "pass"])
            updater.run_command([updater.python_cmd, "-c", "pass"])

        clear_dll_directory.assert_called_once_with()
        self.assertEqual(run.call_count, 2)

    def test_windows_dll_sanitation_failure_prevents_subprocess(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            updater = main.PipUpdate(python_cmd="/target/python")

        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(
            updater,
            "_clear_windows_dll_directory",
            side_effect=OSError("failed"),
        ), mock.patch("main.subprocess.run") as run:
            with self.assertRaisesRegex(main.PipUpdateError, "Windows environment"):
                updater.run_command([updater.python_cmd, "-c", "pass"])

        run.assert_not_called()

    def test_windows_zero_dll_result_uses_winerror_and_prevents_subprocess(self):
        ctypes_module = mock.Mock()
        ctypes_module.windll.kernel32.SetDllDirectoryW.return_value = 0
        ctypes_module.WinError.return_value = OSError(5, "Access is denied")

        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "platform", "win32"
        ), mock.patch.object(
            sys, "executable", "/app/PIP-Updater"
        ), mock.patch.dict(
            sys.modules, {"ctypes": ctypes_module}
        ), mock.patch(
            "main.subprocess.run"
        ) as run:
            with self.assertRaisesRegex(
                main.PipUpdateError, "Windows environment.*Access is denied"
            ):
                main.PipUpdate(python_cmd="/target/python").run()

        ctypes_module.windll.kernel32.SetDllDirectoryW.assert_called_once_with(None)
        ctypes_module.WinError.assert_called_once_with()
        ctypes_module.get_last_error.assert_not_called()
        run.assert_not_called()

    def test_unsupported_frozen_platform_fails_before_subprocess(self):
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "platform", "unsupported-os"
        ), mock.patch("main.subprocess.run") as run:
            with self.assertRaisesRegex(
                main.PipUpdateError, "supported only on Windows, macOS, and Linux"
            ):
                main.PipUpdate(python_cmd="/target/python").run()

        run.assert_not_called()

    def test_cli_parser_passes_python_to_updater(self):
        with mock.patch("main.configure_logging"), mock.patch(
            "main.PipUpdate"
        ) as updater_class:
            exit_status = main.main(
                ["--dry-run", "--python", "/target/python"]
            )

        self.assertEqual(exit_status, 0)
        updater_class.assert_called_once_with(
            dry_run=True, python_cmd="/target/python"
        )
        updater_class.return_value.run.assert_called_once_with()

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
