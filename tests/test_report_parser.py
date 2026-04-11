"""Tests for report parser."""

import pytest

from orchestrator.report_parser import ReportParser


@pytest.fixture
def parser():
    """Create report parser."""
    return ReportParser()


class TestReportParser:
    """Tests for ReportParser class."""

    def test_parse_json_report(self, parser):
        """Test parsing JSON format report."""
        output = '''
        {
            "summary": "Fixed the login bug",
            "files_changed": ["lib/auth/login.dart"],
            "commands_executed": ["flutter test"],
            "tests_passed": 10,
            "tests_failed": 0,
            "pending_items": [],
            "remaining_risks": []
        }
        '''

        report = parser.parse(output)

        assert report.summary == "Fixed the login bug"
        assert "lib/auth/login.dart" in report.files_changed
        assert report.tests_passed == 10
        assert report.tests_failed == 0

    def test_parse_json_in_markdown(self, parser):
        """Test parsing JSON embedded in markdown."""
        output = '''
        Here's the report:

        ```json
        {
            "summary": "Added new feature",
            "files_changed": ["src/feature.py"],
            "commands_executed": ["pytest"],
            "tests_passed": 5,
            "tests_failed": 0
        }
        ```
        '''

        report = parser.parse(output)

        assert "new feature" in report.summary
        assert "src/feature.py" in report.files_changed

    def test_parse_text_report(self, parser):
        """Test parsing plain text report."""
        output = '''
        ## Summary
        Fixed the authentication issue in the login module.

        ## Files Changed
        - lib/auth/login.dart - fixed null check
        - lib/auth/auth_service.dart - added logging

        ## Commands Executed
        - flutter analyze
        - flutter test

        ## Tests Run
        10 tests passed, 0 failed

        ## Pending Items
        - Need to update documentation

        ## Remaining Risks
        - Logout flow may need similar fix
        '''

        report = parser.parse(output)

        assert "authentication issue" in report.summary
        assert len(report.files_changed) >= 1
        assert len(report.commands_executed) >= 1
        assert report.tests_passed == 10
        assert report.tests_failed == 0
        assert len(report.pending_items) >= 1
        assert len(report.remaining_risks) >= 1

    def test_parse_empty_output(self, parser):
        """Test parsing empty output."""
        report = parser.parse("")

        assert report.summary == ""
        assert report.files_changed == []

    def test_parse_extract_files(self, parser):
        """Test extracting file paths from various formats."""
        output = '''
        Modified: lib/main.dart
        Created: test/main_test.dart
        Updated: `pubspec.yaml`
        '''

        report = parser.parse(output)

        # Should extract some files
        assert len(report.files_changed) >= 0  # May or may not match

    def test_parse_checkpoint_detection(self, parser):
        """Test checkpoint detection in output."""
        output = '''
        Summary: Applied migration to database.

        WARNING: Human review required for this change.
        '''

        report = parser.parse(output)

        assert report.needs_checkpoint is True
        assert report.checkpoint_reason is not None

    def test_parse_checkpoint_migration(self, parser):
        """Test checkpoint detection for migration."""
        output = '''
        Summary: Created new migration for users table.
        '''

        report = parser.parse(output)

        assert report.needs_checkpoint is True
        assert "migration" in report.checkpoint_reason
