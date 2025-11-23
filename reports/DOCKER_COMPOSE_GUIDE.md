# Docker Compose Guide

This guide explains how to use the centralized `docker-compose.yml` file to run your Docker containers.

## Quick Start

### Build and Start Containers

```bash
# Build and start both containers in detached mode
docker-compose up -d

# Build and start both containers (interactive, see logs)
docker-compose up

# Build specific service
docker-compose build datapipeline
docker-compose build models
```

### Run Commands in Containers

#### Option 1: Run commands via docker-compose (Recommended)

```bash
# Run a one-time command in datapipeline container
docker-compose run --rm datapipeline bash -c "source /home/app/.venv/bin/activate && python preprocess_clean.py"

# Run a one-time command in models container
docker-compose run --rm models bash -c "source /home/app/.venv/bin/activate && python train_model.py"

# Start interactive shell
docker-compose run --rm datapipeline
docker-compose run --rm models
```

#### Option 2: Execute commands in running containers

```bash
# First, start containers
docker-compose up -d

# Then execute commands
docker-compose exec datapipeline bash -c "source /home/app/.venv/bin/activate && python your_script.py"
docker-compose exec models bash -c "source /home/app/.venv/bin/activate && python train_model.py"

# Interactive shell in running container
docker-compose exec datapipeline bash
docker-compose exec models bash
```

#### Option 3: Set default command in docker-compose.yml

Edit `docker-compose.yml` and uncomment/modify the `command:` line for the service:

```yaml
services:
  datapipeline:
    # ... other config ...
    command: ["-c", "source /home/app/.venv/bin/activate && python preprocess_clean.py"]
```

Then run:
```bash
docker-compose up datapipeline
```

## Common Tasks

### Stop Containers

```bash
# Stop and remove containers
docker-compose down

# Stop containers but keep them
docker-compose stop
```

### View Logs

```bash
# View logs for all services
docker-compose logs

# View logs for specific service
docker-compose logs datapipeline
docker-compose logs models

# Follow logs (like tail -f)
docker-compose logs -f datapipeline
```

### Rebuild After Changes

```bash
# Rebuild and restart
docker-compose up --build

# Rebuild specific service
docker-compose up --build datapipeline
```

## Where to Put Your Commands

### For One-Time or Experimental Commands
Use `docker-compose run` (Option 1 above). This is the most flexible approach.

### For Regular/Default Commands
1. **In docker-compose.yml**: Uncomment and modify the `command:` line (Option 3 above)
2. **Create shell scripts**: Put them in the respective directories and reference them in docker-compose.yml

### Example: Adding a Script to Run

If you have a script you run regularly, you can:

1. Add it to the container (already copied by Dockerfile)
2. Create a helper script in the service directory
3. Run it via docker-compose:

```bash
docker-compose run --rm datapipeline bash -c "source /home/app/.venv/bin/activate && python upload_fake_data.py"
```

## Volume Mounts

The docker-compose.yml already includes:
- `./secrets` mounted to `/home/app/.config/gcloud:ro` (read-only)

You can add additional volumes by uncommenting/modifying the volumes section:
```yaml
volumes:
  - ./data:/app/data:rw  # Mount local ./data to /app/data in container
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs <service-name>

# Try rebuilding
docker-compose up --build
```

### Need to rebuild after dependency changes
```bash
# Force rebuild without cache
docker-compose build --no-cache datapipeline
```

### Need root access (not recommended, but possible)
Add `user: root` to the service in docker-compose.yml (default is non-root user `app`)

