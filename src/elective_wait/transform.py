"""Run the dbt project and validate the MetricFlow semantic manifest."""

from __future__ import annotations

import subprocess

from elective_wait.runtime import TRANSFORM, WAREHOUSE_DIR, project_env, tool


def build_marts() -> None:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    env = project_env()
    subprocess.run(
        [tool("dbt"), "build", "--project-dir", str(TRANSFORM), "--profiles-dir", str(TRANSFORM)],
        cwd=TRANSFORM,
        env=env,
        check=True,
    )
    subprocess.run(
        [tool("mf"), "validate-configs"],
        cwd=TRANSFORM,
        env=env,
        check=True,
    )


def main() -> None:
    build_marts()


if __name__ == "__main__":
    main()
