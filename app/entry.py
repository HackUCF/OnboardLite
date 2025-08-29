# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import os
import subprocess
import sys


# Define the default command to run granian with environment variables
def run_granian():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    workers = os.getenv("ONBOARD_WORKERS", "2")

    command = [
        "uv",
        "run",
        "-m",
        "uvicorn",
        "--host",
        host,
        "--port",
        port,
        "--workers",
        workers,
        "app.main:app",
    ]

    subprocess.run(command)


# Define the default command to run uvicorn with environment variables
def run_uvicorn():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    proxy_headers = os.getenv("ONBOARD_PROXY_HEADERS")
    forwarded_allow_ips = os.getenv("ONBOARD_FORWARDED_ALLOW_IPS")

    command = [
        "uv",
        "run",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        port,
        "--workers",
        "2",
    ]

    if forwarded_allow_ips is not None:
        command.extend(["--forwarded-allow-ips", forwarded_allow_ips])
        command.append("--proxy-headers")

    subprocess.run(command)


def run_dev():
    host = os.getenv("ONBOARD_HOST", "0.0.0.0")
    port = os.getenv("ONBOARD_PORT", "8000")
    command = ["uv", "run", "-m", "uvicorn", "app.main:app", "--host", host, "--port", port, "--reload"]
    subprocess.run(command)


# Define the migrate command
def run_migrate():
    os.chdir("./app")
    command = ["uv", "run", "-m", "alembic", "upgrade", "head"]
    subprocess.run(command)


# Entry point
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        run_migrate()
    elif len(sys.argv) > 1 and sys.argv[1] == "dev":
        run_dev()
    elif len(sys.argv) > 1 and sys.argv[1] == "granian":
        run_granian()
    elif len(sys.argv) > 1 and sys.argv[1] == "uvicorn":
        run_uvicorn()
    else:
        run_granian()
