FROM docker.ci.artifacts.walmart.com/gpa-docker/peopleai/mle_ubuntu:0.7.0
COPY --from=docker.ci.artifacts.walmart.com/ghcr-docker-release-remote/astral-sh/uv:latest /uv /uvx /bin/

# Install the project into `/app`
WORKDIR /app

USER root
RUN addgroup --system --gid 10000 app || true && \
    (id -u app &>/dev/null || adduser --system --uid 10000 --shell /sbin/nologin --home /app --ingroup app app) && \
    chown -R 10000:10001 /app
USER 10000

COPY --chown=10000:10001 pyproject.toml /app/pyproject.toml

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile
COPY --chown=10000:10001 uv.lock /app/uv.lock
RUN uv sync --no-dev --no-editable

# Then, add the rest of the project source code and install it
COPY --chown=10000:10001 . /app

# Remove unnecessary files from the virtual environment before copying
RUN find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + && \
    find /app/.venv -name '*.pyc' -delete && \
    find /app/.venv -name '*.pyo' -delete && \
    echo "Cleaned up .venv"

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD [ "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000" ]