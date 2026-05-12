import tempfile
from pathlib import Path

from examples.full_recherche.demo import run_demo


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="full_recherche_") as tmpdir:
        run_demo(Path(tmpdir))


if __name__ == "__main__":
    main()
