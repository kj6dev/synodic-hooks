"""
Tests for claude/hook_utils.py
Comprehensive coverage for hook utility functions
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch


# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "claude"))
from hook_utils import (
    command_exists,
    get_bash_command,
    get_file_paths,
    get_hook_data,
    get_project_dir,
    get_tool_input,
    get_tool_name,
    play_sound,
    resolve_file_path,
    run_command,
    should_process_tool,
    EDIT_TOOLS,
    SOUND_SOSUMI,
)


class TestGetHookData:
    """Test get_hook_data function"""

    def test_returns_empty_dict_when_stdin_is_tty(self):
        """Should return empty dict when stdin is a TTY"""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = get_hook_data()
            assert result == {}

    def test_parses_valid_json_from_stdin(self):
        """Should parse valid JSON from stdin"""
        test_data = {"tool_name": "Edit", "file_path": "/test.py"}
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with patch("json.load", return_value=test_data):
                result = get_hook_data()
                assert result == test_data

    def test_returns_empty_dict_on_json_decode_error(self):
        """Should return empty dict on JSON decode error"""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with patch("json.load", side_effect=json.JSONDecodeError("err", "doc", 0)):
                result = get_hook_data()
                assert result == {}

    def test_returns_empty_dict_on_general_exception(self):
        """Should return empty dict on any exception"""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with patch("json.load", side_effect=Exception("test error")):
                result = get_hook_data()
                assert result == {}


class TestGetToolName:
    """Test get_tool_name function"""

    def test_extracts_tool_name_from_hook_data(self):
        """Should extract tool name from hook data"""
        hook_data = {"tool_name": "Edit"}
        assert get_tool_name(hook_data) == "Edit"

    def test_returns_unknown_when_tool_name_missing(self):
        """Should return 'Unknown' when tool_name not in data"""
        hook_data = {}
        assert get_tool_name(hook_data) == "Unknown"


class TestGetToolInput:
    """Test get_tool_input function"""

    def test_extracts_tool_input_from_hook_data(self):
        """Should extract tool_input from hook data"""
        tool_input = {"file_path": "/test.py", "command": "ls"}
        hook_data = {"tool_input": tool_input}
        assert get_tool_input(hook_data) == tool_input

    def test_returns_empty_dict_when_tool_input_missing(self):
        """Should return empty dict when tool_input not in data"""
        hook_data = {}
        assert get_tool_input(hook_data) == {}


class TestGetBashCommand:
    """Test get_bash_command function"""

    def test_extracts_bash_command_from_bash_tool(self):
        """Should extract command when tool is Bash"""
        hook_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
        assert get_bash_command(hook_data) == "git status"

    def test_returns_empty_string_for_non_bash_tool(self):
        """Should return empty string when tool is not Bash"""
        hook_data = {
            "tool_name": "Edit",
            "tool_input": {"command": "git status"},
        }
        assert get_bash_command(hook_data) == ""

    def test_returns_empty_string_when_command_missing(self):
        """Should return empty string when command not in tool_input"""
        hook_data = {
            "tool_name": "Bash",
            "tool_input": {},
        }
        assert get_bash_command(hook_data) == ""


class TestGetFilePaths:
    """Test get_file_paths function"""

    def test_extracts_file_path_from_tool_input(self):
        """Should extract file_path from tool_input"""
        hook_data = {"tool_input": {"file_path": "/test/file.py"}}
        assert get_file_paths(hook_data) == ["/test/file.py"]

    def test_falls_back_to_environment_variable(self, monkeypatch):
        """Should fall back to CLAUDE_FILE_PATHS environment variable"""
        monkeypatch.setenv("CLAUDE_FILE_PATHS", "/file1.py /file2.py")
        hook_data = {"tool_input": {}}
        result = get_file_paths(hook_data)
        assert result == ["/file1.py", "/file2.py"]

    def test_returns_empty_list_when_no_file_paths(self, monkeypatch):
        """Should return empty list when no file paths available"""
        monkeypatch.delenv("CLAUDE_FILE_PATHS", raising=False)
        hook_data = {"tool_input": {}}
        assert get_file_paths(hook_data) == []

    def test_calls_get_hook_data_when_hook_data_none(self):
        """Should call get_hook_data() when hook_data parameter is None"""
        with patch("hook_utils.get_hook_data") as mock_get:
            mock_get.return_value = {"tool_input": {"file_path": "/test.py"}}
            result = get_file_paths(None)
            mock_get.assert_called_once()
            assert result == ["/test.py"]


class TestGetProjectDir:
    """Test get_project_dir function"""

    def test_returns_project_dir_from_environment(self, monkeypatch):
        """Should return project directory from CLAUDE_PROJECT_DIR"""
        test_dir = "/test/project"
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", test_dir)
        result = get_project_dir()
        assert result == Path(test_dir)

    def test_falls_back_to_current_directory(self, monkeypatch):
        """Should fall back to cwd when CLAUDE_PROJECT_DIR not set"""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        result = get_project_dir()
        assert result == Path(os.getcwd())


class TestResolveFilePath:
    """Test resolve_file_path function"""

    def test_handles_absolute_path(self, tmp_path):
        """Should handle absolute paths correctly"""
        test_file = tmp_path / "test.py"
        test_file.touch()
        result = resolve_file_path(str(test_file), tmp_path)
        assert result == test_file

    def test_handles_relative_path(self, tmp_path):
        """Should resolve relative paths correctly"""
        test_file = tmp_path / "test.py"
        test_file.touch()
        result = resolve_file_path("test.py", tmp_path)
        assert result == test_file

    def test_returns_none_when_file_does_not_exist(self, tmp_path):
        """Should return None when file doesn't exist"""
        result = resolve_file_path("nonexistent.py", tmp_path)
        assert result is None


class TestPlaySound:
    """Test play_sound function"""

    def test_plays_sound_successfully(self):
        """Should play sound successfully"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = play_sound(SOUND_SOSUMI)
            assert result is True
            mock_run.assert_called_once()

    def test_handles_subprocess_exception(self):
        """Should handle subprocess exceptions gracefully"""
        with patch("subprocess.run", side_effect=Exception("test error")):
            result = play_sound(SOUND_SOSUMI)
            assert result is False

    def test_handles_timeout(self):
        """Should handle timeout exceptions"""
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("afplay", 5)
        ):
            result = play_sound(SOUND_SOSUMI, timeout=1)
            assert result is False


class TestRunCommand:
    """Test run_command function"""

    def test_runs_command_successfully(self):
        """Should run command and return True on success"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = run_command(["echo", "test"])
            assert result is True

    def test_returns_false_on_non_zero_exit(self):
        """Should return False on non-zero exit code"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")
            result = run_command(["false"])
            assert result is False

    def test_handles_timeout_expired(self):
        """Should handle timeout exceptions"""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = run_command(["sleep", "100"], timeout=1)
            assert result is False

    def test_handles_file_not_found(self):
        """Should handle FileNotFoundError"""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = run_command(["nonexistent_command"])
            assert result is False

    def test_handles_general_exception(self):
        """Should handle general exceptions"""
        with patch("subprocess.run", side_effect=Exception("test error")):
            result = run_command(["test"])
            assert result is False

    def test_respects_show_output_flag(self, capsys):
        """Should respect show_output parameter"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="output", stderr="")
            run_command(["test"], show_output=False)
            captured = capsys.readouterr()
            assert captured.out == ""


class TestCommandExists:
    """Test command_exists function"""

    def test_returns_true_when_command_exists(self):
        """Should return True when command exists"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = command_exists("ls")
            assert result is True

    def test_returns_false_when_command_does_not_exist(self):
        """Should return False when command doesn't exist"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            result = command_exists("nonexistent_command_xyz")
            assert result is False


class TestShouldProcessTool:
    """Test should_process_tool function"""

    def test_returns_true_when_tool_in_allowed_list(self):
        """Should return True when tool is in allowed list"""
        assert should_process_tool("Edit", EDIT_TOOLS) is True

    def test_returns_false_when_tool_not_in_allowed_list(self):
        """Should return False when tool not in allowed list"""
        assert should_process_tool("Read", EDIT_TOOLS) is False
