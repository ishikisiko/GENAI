from __future__ import annotations

from pathlib import Path


def test_frontend_call_chain_not_rerouted():
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    assert src_root.exists()

    for file_path in src_root.rglob("*.ts*"):
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8")
        assert "from backend." not in content
        assert "import backend." not in content
