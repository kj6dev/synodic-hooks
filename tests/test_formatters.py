"""
Tests for formatters package
Tests formatter registry and individual language formatters
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch


# Add formatters to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from formatters import (
    get_formatter,
    get_supported_extensions,
    register_formatter,
)


class TestFormatterRegistry:
    """Test formatter registry functions"""

    def test_register_formatter(self):
        """Should register formatter for extensions"""

        def mock_formatter(file_path: Path, project_dir: Path) -> bool:
            return True

        # Register a test extension
        register_formatter([".test"], mock_formatter)

        # Verify it's registered
        formatter = get_formatter(Path("file.test"))
        assert formatter is not None
        assert formatter == mock_formatter

    def test_register_formatter_case_insensitive(self):
        """Should register formatters case-insensitively"""

        def mock_formatter(file_path: Path, project_dir: Path) -> bool:
            return True

        register_formatter([".TEST"], mock_formatter)

        # Should find with lowercase
        formatter = get_formatter(Path("file.test"))
        assert formatter == mock_formatter

    def test_get_formatter_returns_none_for_unregistered(self):
        """Should return None for unregistered extensions"""
        formatter = get_formatter(Path("file.xyz"))
        assert formatter is None

    def test_get_formatter_handles_no_extension(self):
        """Should handle files without extensions"""
        formatter = get_formatter(Path("README"))
        assert formatter is None

    def test_get_supported_extensions(self):
        """Should return list of supported extensions"""
        extensions = get_supported_extensions()
        assert isinstance(extensions, list)
        # Check for known extensions
        assert ".py" in extensions
        assert ".swift" in extensions
        assert ".ts" in extensions
        assert ".json" in extensions


class TestPythonFormatter:
    """Test Python formatter"""

    def test_python_formatter_registered(self):
        """Should have Python formatter registered"""
        formatter = get_formatter(Path("test.py"))
        assert formatter is not None

    def test_formats_python_file(self, tmp_path):
        """Should format Python files with uv + ruff"""
        # Create a test Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nimport sys\n\n\ndef  test( ):\n    pass\n")

        formatter = get_formatter(test_file)

        with patch("subprocess.run") as mock_run:
            # Mock successful formatting
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Run formatter
            result = formatter(test_file, tmp_path)

            # Should have called uv run ruff
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "uv" or "uv" in call_args[0]
            assert "ruff" in call_args

    def test_handles_uv_not_installed(self, tmp_path):
        """Should handle missing uv gracefully"""
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        formatter = get_formatter(test_file)

        # Mock command_exists in claude.hook_utils to return False for uv
        with patch("claude.hook_utils.command_exists", return_value=False):
            result = formatter(test_file, tmp_path)
            # Should return True (skip formatting) when uv not found
            assert result is True


class TestSwiftFormatter:
    """Test Swift formatter"""

    def test_swift_formatter_registered(self):
        """Should have Swift formatter registered"""
        formatter = get_formatter(Path("test.swift"))
        assert formatter is not None

    def test_formats_swift_file(self, tmp_path):
        """Should format Swift files"""
        test_file = tmp_path / "test.swift"
        test_file.write_text('import Foundation\nfunc test(){print("test")}')

        formatter = get_formatter(test_file)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = formatter(test_file, tmp_path)

            # Should have called formatting tools
            assert mock_run.called

    def test_handles_swift_tools_not_installed(self, tmp_path):
        """Should handle missing Swift tools gracefully"""
        test_file = tmp_path / "test.swift"
        test_file.write_text("func test() { }")

        formatter = get_formatter(test_file)

        # Mock command_exists in claude.hook_utils to return False for all Swift tools
        with patch("claude.hook_utils.command_exists", return_value=False):
            result = formatter(test_file, tmp_path)
            # Swift formatter returns True even when tools missing (warnings only)
            assert result is True


class TestTypeScriptFormatter:
    """Test TypeScript formatter"""

    def test_typescript_formatter_registered(self):
        """Should have TypeScript formatter registered for .ts"""
        formatter = get_formatter(Path("test.ts"))
        assert formatter is not None

    def test_tsx_formatter_registered(self):
        """Should have TypeScript formatter registered for .tsx"""
        formatter = get_formatter(Path("test.tsx"))
        assert formatter is not None

    def test_formats_typescript_file(self, tmp_path):
        """Should format TypeScript files if package.json exists"""
        test_file = tmp_path / "test.ts"
        test_file.write_text("function test(){return true;}")

        # Create package.json to indicate Node project
        package_json = tmp_path / "package.json"
        package_json.write_text("{}")

        formatter = get_formatter(test_file)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = formatter(test_file, tmp_path)

            # Should have called prettier
            assert mock_run.called

    def test_skips_formatting_without_package_json(self, tmp_path):
        """Should skip formatting if no package.json (not a Node project)"""
        test_file = tmp_path / "test.ts"
        test_file.write_text("function test(){return true;}")

        formatter = get_formatter(test_file)

        with patch("subprocess.run") as mock_run:
            result = formatter(test_file, tmp_path)

            # Should not call prettier if no package.json
            assert not mock_run.called
            # Should still return True (skip silently)
            assert result is True


class TestJSONFormatter:
    """Test JSON formatter"""

    def test_json_formatter_registered(self):
        """Should have JSON formatter registered"""
        formatter = get_formatter(Path("test.json"))
        assert formatter is not None

    def test_formats_json_file(self, tmp_path):
        """Should format JSON files"""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key":"value","nested":{"data":123}}')

        formatter = get_formatter(test_file)

        # JSON formatter uses native Python json module
        result = formatter(test_file, tmp_path)

        # Should format the file
        formatted = test_file.read_text()
        assert "\n" in formatted  # Should be pretty-printed
        assert "  " in formatted  # Should have indentation

    def test_handles_invalid_json(self, tmp_path):
        """Should handle invalid JSON gracefully"""
        test_file = tmp_path / "test.json"
        test_file.write_text("{invalid json")

        formatter = get_formatter(test_file)

        result = formatter(test_file, tmp_path)
        # Should return False on invalid JSON
        assert result is False


class TestFormatterIntegration:
    """Integration tests for formatters"""

    def test_all_formatters_have_consistent_signature(self):
        """All formatters should have consistent function signature"""
        extensions = get_supported_extensions()

        for ext in extensions:
            formatter = get_formatter(Path(f"test{ext}"))
            assert formatter is not None
            assert callable(formatter)

            # Should accept (Path, Path) -> bool
            # Test with mock paths (don't actually call)
            import inspect

            sig = inspect.signature(formatter)
            params = list(sig.parameters.values())
            assert len(params) == 2

    def test_formatters_registered_for_expected_extensions(self):
        """Check that expected extensions are registered"""
        extensions = get_supported_extensions()

        # Check Python
        assert ".py" in extensions

        # Check Swift
        assert ".swift" in extensions

        # Check TypeScript/JavaScript
        assert ".ts" in extensions
        assert ".tsx" in extensions

        # Check JSON
        assert ".json" in extensions
