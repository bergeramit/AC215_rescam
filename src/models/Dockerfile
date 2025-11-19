# Use the specified base image
FROM --platform=linux/amd64 python:3.12-slim

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Tell uv to copy packages from the wheel into the site-packages
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/home/app/.venv

# Update package lists and install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and set up the working directory
RUN useradd -m app && \
    mkdir -p /app && \
    chown app:app /app

# Switch to non-root user
USER app

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml for uv sync to download all necessary dependencies
COPY --chown=app:app src/models/pyproject.toml .

# Install uv, create venv, and install requirements
ENV PATH="/home/app/.local/bin:$PATH"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && uv sync

# Set environment variables
ENV PATH="/home/app/.venv/bin:$PATH"

# Copy model files
COPY --chown=app:app src/models/train_model.py .
COPY --chown=app:app src/models/infer_model.py .
COPY --chown=app:app src/models/model_rag.py .
COPY --chown=app:app src/models/firestore_event_handler.py .
COPY --chown=app:app src/models/training_config.json .

RUN mkdir -p ./protobuf_schema
COPY --chown=app:app src/models/protobuf_schema/firestore_message_pb2.py ./protobuf_schema/
COPY --chown=app:app src/models/protobuf_schema/__init__.py ./protobuf_schema/

# Create the gcloud config directory (volume mount will provide credentials)
RUN mkdir -p /home/app/.config/gcloud

# Set PORT for Cloud Run (defaults to 8080, but Cloud Run will override this)
ENV PORT=8080

# Set the entrypoint and default command
# For interactive use, docker-shell.sh will override this with bash
# For Cloud Run, use uvicorn with PORT from environment variable
ENTRYPOINT ["/bin/bash"]
CMD ["-c", "source /home/app/.venv/bin/activate && /bin/bash"]
