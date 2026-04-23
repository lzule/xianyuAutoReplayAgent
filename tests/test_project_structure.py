from pathlib import Path


def test_expected_directories_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = [
        root / "app",
        root / "configs",
        root / "knowledge",
        root / "scripts",
        root / "tests",
        root / "docs",
        root / "data",
    ]
    for path in expected:
        assert path.exists(), f"缺少目录: {path}"
