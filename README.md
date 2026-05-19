# lccfq-backend

Stateful, queueing backend to connect an HPC system to a QPU.

## Setup

Copy the example config and edit it for your environment:

```bash
cp configs/example_config.toml config.toml
```

## CLI

All commands are run via `uv run backend`.

### Starting the server

```bash
uv run backend start
uv run backend start -c /path/to/config.toml
```

### Certificate management

Server certificates must be set up before starting the server. Client certificates are issued to users who need to connect to the backend's gRPC API.

**Set up CA and server certificates:**
```bash
uv run backend cert setup-server
uv run backend cert setup-server --cert-dir ./certs --hostname localhost
```

**Create a client certificate for a user:**
```bash
uv run backend cert create-client <user_id>
uv run backend cert create-client <user_id> --cert-dir ./certs
```

**List existing client certificates:**
```bash
uv run backend cert list-clients
```

**Check server certificate status:**
```bash
uv run backend cert status
```

### Logging

Log level is set via `log_level` in `config.toml`. It can also be overridden with the `LCCFQ_LOG_LEVEL` environment variable. Additional options:

| Variable | Description |
|---|---|
| `LCCFQ_LOG_LEVEL` | Global log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LCCFQ_LOG_LEVELS` | Per-component overrides, e.g. `lccfq.executor=DEBUG,lccfq.hwman=WARNING` |
| `LCCFQ_LOG_FORMAT` | `text` (default) or `json` |
| `LCCFQ_LOG_FILE` | Path to log file (enables rotating file handler) |
