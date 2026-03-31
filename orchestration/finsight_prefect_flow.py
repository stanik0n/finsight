import argparse
import os
import subprocess
from datetime import date, timedelta

from prefect import flow, task, get_run_logger


def _target_date(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)

    candidate = date.today() - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


@task(log_prints=True)
def run_step(step_name: str, command: list[str], extra_env: dict | None = None) -> None:
    logger = get_run_logger()
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    logger.info("Starting %s", step_name)
    result = subprocess.run(
        command,
        env=env,
        cwd="/opt/finsight",
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{step_name} failed with exit code {result.returncode}")
    logger.info("Finished %s", step_name)


@flow(name="finsight-daily")
def finsight_daily(target_date: str | None = None) -> None:
    ds = _target_date(target_date).isoformat()
    dbt_env = {"DUCKDB_PATH": os.environ.get("DUCKDB_PATH", "/data/finsight.duckdb")}

    run_step.submit(
        "ingest_alpaca_bars",
        ["python", "ingestion/alpaca_batch.py", ds],
    ).result()

    run_step.submit(
        "validate_bronze",
        ["python", "orchestration/scripts/validate_bronze.py", ds],
    ).result()

    run_step.submit(
        "spark_transform",
        ["python", "spark/transform.py", ds],
    ).result()

    run_step.submit(
        "load_silver_to_duckdb",
        ["python", "orchestration/scripts/load_silver_to_duckdb.py", ds],
    ).result()

    run_step.submit(
        "dbt_deps",
        [
            "dbt",
            "deps",
            "--project-dir",
            "/opt/finsight/dbt_finsight",
            "--profiles-dir",
            "/opt/finsight/dbt_finsight",
        ],
        extra_env=dbt_env,
    ).result()

    run_step.submit(
        "dbt_seed",
        [
            "dbt",
            "seed",
            "--project-dir",
            "/opt/finsight/dbt_finsight",
            "--profiles-dir",
            "/opt/finsight/dbt_finsight",
            "--target",
            "prod",
        ],
        extra_env=dbt_env,
    ).result()

    run_step.submit(
        "dbt_run",
        [
            "dbt",
            "run",
            "--project-dir",
            "/opt/finsight/dbt_finsight",
            "--profiles-dir",
            "/opt/finsight/dbt_finsight",
            "--target",
            "prod",
        ],
        extra_env=dbt_env,
    ).result()

    run_step.submit(
        "dbt_test",
        [
            "dbt",
            "test",
            "--project-dir",
            "/opt/finsight/dbt_finsight",
            "--profiles-dir",
            "/opt/finsight/dbt_finsight",
            "--target",
            "prod",
        ],
        extra_env=dbt_env,
    ).result()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FinSight Phase 1 daily Prefect flow.")
    parser.add_argument("--date", dest="target_date", help="Trading date in YYYY-MM-DD format")
    args = parser.parse_args()
    finsight_daily(target_date=args.target_date)
