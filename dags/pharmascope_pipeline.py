"""Optional Airflow DAG skeleton for PharmaScope.

This DAG is a documentation/orchestration stub. Local development should use
``PipelineRunner`` / CLI scripts so the project works without an Airflow server.

Do not schedule large downloads by default.
"""

from __future__ import annotations

# Airflow imports are optional at runtime for local users without Airflow installed.
try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from datetime import datetime, timedelta

    default_args = {
        "owner": "pharmascope",
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    }

    with DAG(
        dag_id="pharmascope_openfda_bounded",
        default_args=default_args,
        description="Bounded OpenFDA extract + transform (dev-safe limits)",
        schedule=None,  # manual trigger only
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["pharmascope", "openfda"],
    ) as dag:
        extract = BashOperator(
            task_id="extract_events_bounded",
            bash_command="python scripts/download_data.py --source openfda_events --limit 200",
        )
        transform = BashOperator(
            task_id="transform_events",
            bash_command="python scripts/run_transformations.py --source openfda_events",
        )
        analytics = BashOperator(
            task_id="run_analytics",
            bash_command="python scripts/run_analytics.py",
        )
        extract >> transform >> analytics

except ImportError:
    dag = None  # Airflow not installed in this environment
