import tempfile
from pathlib import Path

from examples.architect_lite.demo import run_demo


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="architect_lite_") as tmpdir:
        run_demo(Path(tmpdir))


if __name__ == "__main__":
    main()
