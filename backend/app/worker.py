import os
import socket

from .models import (
    SessionLocal,
    Build,
    get_utc_now,
)

from .docker_runner import run_in_docker
from .queue import redis_conn


MAX_RETRIES = int(
    os.getenv("MAX_RETRIES", "2")
)


def append_log(
    db,
    build_id,
    line,
):
    """
    Save logs to PostgreSQL and publish them
    through Redis for WebSocket clients.
    """

    build = (
        db.query(Build)
        .filter(Build.id == build_id)
        .first()
    )

    if build:

        build.logs += line
        db.commit()

    redis_conn.publish(
        f"build-logs:{build_id}",
        line
    )


def run_build(build_id: str):

    db = SessionLocal()

    try:

        build = (
            db.query(Build)
            .filter(Build.id == build_id)
            .first()
        )

        if not build:
            return

        worker_name = socket.gethostname()

        # -----------------------------------------------------
        # Mark running
        # -----------------------------------------------------

        build.status = "running"
        build.started_at = get_utc_now()

        db.commit()

        append_log(
            db,
            build_id,
            (
                "\n========================================\n"
                f"BUILD {build_id}\n"
                "========================================\n"
                f"Worker: {worker_name}\n"
                "Execution mode: distributed RQ worker\n"
                f"Repository: {build.repo_url}\n"
                f"Branch: {build.branch}\n"
                f"Attempt: {build.retry_count + 1}/"
                f"{MAX_RETRIES + 1}\n"
                "========================================\n\n"
            ),
        )

        append_log(
            db,
            build_id,
            (
                f"Worker {worker_name} "
                "is starting Docker execution...\n"
            ),
        )

        # -----------------------------------------------------
        # Docker log callback
        # -----------------------------------------------------

        def log_cb(line):

            append_log(
                db,
                build_id,
                line,
            )

        # -----------------------------------------------------
        # Execute build/test pipeline
        # -----------------------------------------------------

        exit_code = run_in_docker(
            image=build.image,
            repo_url=build.repo_url,
            branch=build.branch,
            steps=build.steps,
            log_callback=log_cb,
        )

        # Refresh database object.
        build = (
            db.query(Build)
            .filter(Build.id == build_id)
            .first()
        )

        build.exit_code = exit_code

        # -----------------------------------------------------
        # SUCCESS
        #
        # This means:
        #
        # - build succeeded
        # - and if tests existed, tests succeeded
        #
        # If there were no tests, build-only success is also
        # represented as "passed".
        # -----------------------------------------------------

        if exit_code == 0:

            build.status = "passed"
            build.finished_at = get_utc_now()

            db.commit()

            append_log(
                db,
                build_id,
                (
                    "\n========================================\n"
                    "BUILD PIPELINE PASSED\n"
                    "========================================\n"
                ),
            )

        # -----------------------------------------------------
        # FAILURE + RETRY AVAILABLE
        # -----------------------------------------------------

        elif build.retry_count < MAX_RETRIES:

            build.retry_count += 1
            build.status = "queued"

            db.commit()

            append_log(
                db,
                build_id,
                (
                    "\n========================================\n"
                    f"BUILD PIPELINE FAILED "
                    f"(exit code {exit_code})\n"
                    "Re-queuing build...\n"
                    f"Retry {build.retry_count}/{MAX_RETRIES}\n"
                    "========================================\n"
                ),
            )

            from .queue import job_queue

            job_queue.enqueue(
                "app.worker.run_build",
                build_id,
            )

            return

        # -----------------------------------------------------
        # FAILURE + NO RETRIES LEFT
        # -----------------------------------------------------

        else:

            build.status = "failed"
            build.finished_at = get_utc_now()

            db.commit()

            append_log(
                db,
                build_id,
                (
                    "\n========================================\n"
                    "BUILD PIPELINE FAILED\n"
                    f"Maximum retries ({MAX_RETRIES}) reached.\n"
                    "========================================\n"
                ),
            )

        redis_conn.publish(
            f"build-logs:{build_id}",
            "__EOF__"
        )

    except Exception as exc:

        build = (
            db.query(Build)
            .filter(Build.id == build_id)
            .first()
        )

        if build:

            build.status = "failed"
            build.finished_at = get_utc_now()

            error_message = (
                f"\nInternal Error: {str(exc)}\n"
            )

            build.logs += error_message

            db.commit()

            redis_conn.publish(
                f"build-logs:{build_id}",
                error_message
            )

            redis_conn.publish(
                f"build-logs:{build_id}",
                "__EOF__"
            )

    finally:

        db.close()