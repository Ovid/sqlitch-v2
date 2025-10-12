from sqlitch import __version__


def test_version_exposes_package_version() -> None:
    assert __version__ == "1.0.0"
