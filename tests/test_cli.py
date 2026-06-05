import subprocess
import sys


def test_brief_command_writes_markdown_under_output_briefings(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "brief",
            "--plan",
            "examples/briefing_plan.example.json",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    briefings_dir = tmp_path / "briefings"
    files = list(briefings_dir.glob("*.md"))
    assert len(files) == 1
    assert "# Personal public-opinion observation Briefing" in files[0].read_text(
        encoding="utf-8"
    )
