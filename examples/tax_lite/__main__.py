import tempfile
from pathlib import Path

from examples.tax_lite.demo import run_demo


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tax_lite_") as tmpdir:
        run_demo(Path(tmpdir))


if __name__ == "__main__":
    main()
