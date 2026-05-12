import tempfile
from pathlib import Path

from examples.cockpit_demo.demo import run_demo


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="cockpit_demo_") as tmpdir:
        run_demo(Path(tmpdir))


if __name__ == "__main__":
    main()
