import tempfile
from pathlib import Path

from examples.hello_world.demo import run_demo


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="hello_world_") as tmpdir:
        run_demo(Path(tmpdir))


if __name__ == "__main__":
    main()
