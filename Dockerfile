# Use the official Python base image
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

# Set the working directory in the container
WORKDIR /src




FROM base AS dev

COPY . .

EXPOSE 8000

ENTRYPOINT ["uv", "run", "-m uvicorn", "app.main:app", "--host 0.0.0.0", "--reload", "--port 8000"]

CMD dev



FROM dev AS test

CMD ["uv", "run", "pytest"]



FROM base as prod

COPY requirements.txt .

RUN uv sync

COPY ./app ./app

EXPOSE 8000

# Start the FastAPI application
ENTRYPOINT ["/bin/python3", "app/entry.py"]

CMD []
