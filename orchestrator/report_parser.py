"""Parser for execution reports."""

import re
from typing import Optional

from .models import ExecutionReport
from .utils import parse_json_from_text


class ReportParser:
    """
    Parses execution output into structured reports.

    Handles various output formats from the executor.
    """

    def parse(self, output: str) -> ExecutionReport:
        """
        Parse execution output into structured report.

        Args:
            output: Raw executor output

        Returns:
            Structured ExecutionReport
        """
        # Try JSON parse first
        json_report = self._try_json_parse(output)
        if json_report:
            return json_report

        # Fall back to text parsing
        return self._parse_text(output)

    def _try_json_parse(self, output: str) -> Optional[ExecutionReport]:
        """Try to parse JSON format report."""
        parsed = parse_json_from_text(output)
        if parsed and isinstance(parsed, dict):
            try:
                return ExecutionReport.model_validate(parsed)
            except Exception:
                pass
        return None

    def _parse_text(self, output: str) -> ExecutionReport:
        """Parse text format report with heuristics."""
        report = ExecutionReport(raw_output=output)

        # Extract summary (first paragraph or section)
        summary = self._extract_summary(output)
        if summary:
            report.summary = summary

        # Extract files changed
        report.files_changed = self._extract_files(output)

        # Extract commands
        report.commands_executed = self._extract_commands(output)

        # Extract test info
        tests_info = self._extract_tests(output)
        report.tests_run = tests_info.get("tests", [])
        report.tests_passed = tests_info.get("passed", 0)
        report.tests_failed = tests_info.get("failed", 0)

        # Extract pending items
        report.pending_items = self._extract_pending(output)

        # Extract risks
        report.remaining_risks = self._extract_risks(output)

        # Check for checkpoint needs
        checkpoint_info = self._check_checkpoint_needed(output)
        report.needs_checkpoint = checkpoint_info[0]
        report.checkpoint_reason = checkpoint_info[1]

        return report

    def _extract_summary(self, text: str) -> str:
        """Extract summary from output."""
        # Look for explicit summary section
        patterns = [
            r"(?:^|\n)(?:##?\s*)?Summary[:\s]*\n(.*?)(?:\n\n|\n#|\Z)",
            r"(?:^|\n)(?:##?\s*)?What was done[:\s]*\n(.*?)(?:\n\n|\n#|\Z)",
            r"(?:^|\n)(?:##?\s*)?Done[:\s]*\n(.*?)(?:\n\n|\n#|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]

        # Default to first paragraph
        paragraphs = text.split("\n\n")
        if paragraphs:
            return paragraphs[0].strip()[:500]

        return text[:500]

    def _extract_files(self, text: str) -> list[str]:
        """Extract file paths from output."""
        files = set()

        # Look for files section
        files_section = re.search(
            r"(?:Files?\s*(?:changed|modified|created|edited))[:\s]*\n(.*?)(?:\n\n|\n#|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if files_section:
            # Extract file paths from section
            for line in files_section.group(1).split("\n"):
                line = line.strip().lstrip("-•*")
                if line and "/" in line or "." in line:
                    # Clean up common patterns
                    filepath = re.sub(r"^\s*`?([^`\s]+)`?\s*.*$", r"\1", line)
                    if filepath:
                        files.add(filepath)

        # Also look for explicit file patterns
        file_patterns = [
            r"(?:modified|edited|created|updated|changed):\s*[`']?([^\s`']+)[`']?",
            r"(?:in|file)\s+[`']([^\s`']+)[`']",
        ]
        for pattern in file_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                files.add(match.group(1))

        return list(files)

    def _extract_commands(self, text: str) -> list[str]:
        """Extract commands executed."""
        commands = []

        # Look for commands section
        cmd_section = re.search(
            r"(?:Commands?\s*(?:executed|run))[:\s]*\n(.*?)(?:\n\n|\n#|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if cmd_section:
            for line in cmd_section.group(1).split("\n"):
                line = line.strip().lstrip("-•*`")
                if line and not line.startswith("#"):
                    commands.append(line.rstrip("`"))

        # Also look for inline command patterns
        inline_cmds = re.findall(r"(?:ran|executed|running):\s*`([^`]+)`", text, re.IGNORECASE)
        commands.extend(inline_cmds)

        return commands[:20]  # Limit

    def _extract_tests(self, text: str) -> dict:
        """Extract test information."""
        result = {"tests": [], "passed": 0, "failed": 0}

        # Look for test summary patterns
        patterns = [
            r"(\d+)\s*(?:tests?\s*)?passed",
            r"passed[:\s]*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["passed"] = int(match.group(1))
                break

        patterns = [
            r"(\d+)\s*(?:tests?\s*)?failed",
            r"failed[:\s]*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["failed"] = int(match.group(1))
                break

        return result

    def _extract_pending(self, text: str) -> list[str]:
        """Extract pending items."""
        pending = []

        # Match sections like "## Pending Items" or "Pending:"
        section = re.search(
            r"(?:##?\s*)?(?:Pending\s*Items?|TODO|Remaining\s*Items?|Not\s*done)[:\s]*\n(.*?)(?:\n\n|\n##|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if section:
            for line in section.group(1).split("\n"):
                line = line.strip().lstrip("-•*[] ")
                if line and not line.startswith("#"):
                    pending.append(line)

        return pending[:10]

    def _extract_risks(self, text: str) -> list[str]:
        """Extract remaining risks."""
        risks = []

        section = re.search(
            r"(?:Risks?|Warnings?|Concerns?|Issues?)[:\s]*\n(.*?)(?:\n\n|\n#|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if section:
            for line in section.group(1).split("\n"):
                line = line.strip().lstrip("-•*")
                if line:
                    risks.append(line)

        return risks[:10]

    def _check_checkpoint_needed(self, text: str) -> tuple[bool, Optional[str]]:
        """Check if checkpoint is needed based on output."""
        checkpoint_patterns = [
            (r"checkpoint\s*required", "explicit_checkpoint"),
            (r"human\s*review\s*(?:required|needed)", "human_review"),
            (r"migration", "migration"),
            (r"delete|remove|drop", "destructive_operation"),
            (r"force\s*push", "force_push"),
        ]

        text_lower = text.lower()
        for pattern, reason in checkpoint_patterns:
            if re.search(pattern, text_lower):
                return True, reason

        return False, None
