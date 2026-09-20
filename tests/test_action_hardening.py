import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USES_PATTERN = re.compile(r"^\s*(?:- )?uses:\s*([^\s#]+)", re.MULTILINE)
IMMUTABLE_ACTION_PATTERN = re.compile(r"[^@]+@[0-9a-f]{40}")


def _uses(path: Path) -> list[str]:
    return USES_PATTERN.findall(path.read_text())


def test_public_action_pins_third_party_actions_to_commits():
    refs = _uses(ROOT / "action.yml")
    assert refs
    assert all(IMMUTABLE_ACTION_PATTERN.fullmatch(ref) for ref in refs)
