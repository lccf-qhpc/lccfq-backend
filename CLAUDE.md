# CLAUDE.md

This file provides comprehensive guidance to AI agents when working with code in this repository.

## What is LCCFQ Backend?

LCCFQ Backend is a stateful, queueing backend service that connects an HPC system (via SLURM) to a Quantum Processing Unit (QPU). It manages quantum task execution with sophisticated state management, context-aware queueing, and SLURM integration for resource scheduling.

## Quick Start

### Configuration

The service is configured via a `config.toml` file in the project root. If no config file exists, the service will use default values.

**Create a configuration file:**
```bash
cp config.toml my_config.toml
# Edit my_config.toml with your settings
```

**Configuration options:**
- `log_level` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `with_watchdog` - Enable/disable watchdog daemon
- `watchdog_interval` - Watchdog check interval in seconds
- `with_grpc` - Enable/disable gRPC server
- `grpc_address` - gRPC server bind address
- `grpc_port` - gRPC server port
- `grpc_max_workers` - Maximum gRPC worker threads
- `cert_dir` - Directory for mTLS certificates
- `hwman_mock_mode` - Use mock hardware manager (true) or real connection (false)
- `hwman_address` - Hardware manager server address
- `hwman_port` - Hardware manager server port
- `hwman_cert_dir` - Directory for hwman client certificates
- `hwman_client_name` - Client name for hwman authentication

See `config.toml` for default values and detailed comments.

### Running the Service

```bash
python src/lccfq_backend/main.py
```

This starts:
1. **Main execution loop** - Polls queue every 10 seconds, executes tasks on QPU
2. **Watchdog daemon thread** - Checks QPU health (configurable via `watchdog_interval` in config)
3. **gRPC server thread** - Listens on configured address:port with mTLS (default `[::]`:50052)

All settings are controlled via `config.toml`. To use a custom config file:

```python
from lccfq_backend.config import BackendSettings

# Load custom config file
settings = BackendSettings(_toml_file="production_config.toml")

# Access settings
print(settings.grpc_port)  # 50052
print(settings.to_dict())  # Get all settings as dict
```

### Development Commands

**Package Management** (uses `uv` with Poetry as fallback):
- Install dependencies: `uv sync` or `poetry install`
- Add a dependency: `uv add <package>` or `poetry add <package>`

**Testing**:
- Run all tests: `pytest` or `poetry run pytest`
- Run specific test file: `pytest src/tests/path/to/test_file.py`
- Run with max failures: `pytest --maxfail=3`
- Test configuration is in `pyproject.toml` under `[tool.pytest.ini_options]`

**Building gRPC Protos**:
```bash
make protos
```

## System Architecture

### Component Interaction Overview

```
┌──────────────────────────┐
│   SLURM (separate HPC)   │
│   - Job scheduler        │  Reads: /tmp/qpu_status.flag (online/offline)
│   - Resource allocator   │  Reads: /tmp/qpu_observables.env (QPU metrics)
└──────────────────────────┘
           │
           │ User: sbatch --gres=qpu:1 job.sh
           ▼
┌──────────────────────────┐
│  User's SLURM Job        │
│  - Allocated QPU access  │
│  - Calls gRPC API ──────────► gRPC Server (mTLS, port 50052)
└──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────┐
│  lccfq-backend (python src/lccfq_backend/main.py)│
│  ┌─────────────────────────────────────────────┐ │
│  │ gRPC Server (api/grpc_server.py)            │ │
│  │ - Accepts task submissions via RPC          │ │
│  │ - Enforces mTLS authentication              │ │
│  │ - Calls executor.execute() to enqueue       │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ Watchdog Thread (daemon/watchdog.py)        │ │
│  │ - Pings QPU via hwman.ping()                │ │
│  │ - Writes /tmp/qpu_status.flag               │ │
│  │ - Exports /tmp/qpu_observables.env          │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ Main Loop                                   │ │
│  │ - Reads /tmp/qpu_status.flag                │ │
│  │ - Calls executor._execute_next()            │ │
│  │ - Processes queue (priority + timestamp)    │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ QPUExecutor (backend/executor.py)           │ │
│  │ - Coordinates queue, FSM, hwman             │ │
│  │ - execute(): enqueues task                  │ │
│  │ - _execute_next(): dequeues & dispatches    │ │
│  │ - _dispatch(): routes by task type          │ │
│  │ - Calls hwman.run_circuit/test/control      │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │ BaseHWManClient (backend/hwman.py)              │ │
│  │ - run_circuit(gates, shots) ───────────────────► Physical QPU
│  │ - run_test(symbol, params, shots)           │ │
│  │ - retune(), get_observables(), ping()       │ │
│  │ (Currently returns mock data)               │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Core Components

**QPU State Machine (`backend/fsm.py`)**
- Manages QPU lifecycle through a finite state machine with 8 states
- States: `INACCESSIBLE` → `ACCESSIBLE` → `RESPONSIVE` → `TUNED` → `IDLE` ⇄ `BUSY`
- Also handles: `MISTUNED`, `UNRESPONSIVE`
- State transitions are triggered by events (connect, tune, task execution, etc.)
- All QPU operations must respect the current state
- Invalid transitions raise `UnknownQPUState`

**Task Queue (`backend/queue.py`)**
- Priority-based deque with context locking
- Supports three task types: `CircuitTask`, `TestTask`, `ControlTask`
- Context system allows batching related tasks for atomic execution
- Tasks with the same `context_id` are dequeued and executed together
- Priority and timestamp determine execution order

**Executor (`backend/executor.py`)**
- Main orchestrator that coordinates queue, state machine, and hardware manager
- **Line 49**: `execute(task, user, ...)` - Entry point to enqueue tasks
- **Line 84**: `_execute_next()` - Dequeues and executes next task (or context batch)
- **Line 138**: `hwman.run_circuit(gates, shots)` - **Actually talks to QPU**
- `_dispatch()`: routes tasks to appropriate execution method by type
- Automatically handles deferred tasks when QPU returns to IDLE
- Handles context batching for atomic execution

**Hardware Manager Client (`backend/hwman.py`)**
- Interface to the actual QPU hardware (currently mocked)
- Methods: `run_circuit()`, `run_test()`, `retune()`, `get_observables()`, `ping()`
- Returns `HWManStatus` (OK, WARNING, ERROR, RETUNE_REQUIRED, etc.)
- **When implementing real hardware, replace mock logic here**

**Watchdog Daemon (`daemon/watchdog.py`)**
- Background thread that periodically checks QPU health
- Writes status to `/tmp/qpu_status.flag` (read by executor and SLURM)
- Queries and exports observables via `slurm/exporter.py`
- Runs every 300 seconds by default, configurable via `interval` parameter

**gRPC Server (`api/grpc_server.py`)**
- Runs in daemon thread alongside main execution loop
- Provides external API for task submission
- Enforces mutual TLS (mTLS) authentication
- Shares the same QPUExecutor instance with main loop
- Gracefully shuts down on SIGTERM/SIGINT

**Executor Service (`api/services/executor_service.py`)**
- Implements gRPC service interface
- Wraps the QPUExecutor instance
- Handles incoming RPC requests and returns responses
- Currently implements `Ping` RPC, extensible for task submission

### Task Types

**CircuitTask**: Execute quantum gates
- Fields: `gates` (list of Gate objects), `shots`
- Returns: `CircuitResult` with distribution dict

**TestTask**: Run quantum benchmarks
- Fields: `symbol` (test name), `params`, `shots`
- Returns: `TestResult` with parameters dict (e.g., fidelity, XEB)
- Note: `TestTask` class has `__test__ = False` to prevent pytest collection

**ControlTask**: QPU control commands
- Commands: `reset`, `retune`, `resetall`, `qtol`
- `qtol`: Quality tolerance check with automatic retune attempts
- Returns: `ControlAck` with status and message

### Execution Context

Tasks can optionally specify a `QPUExecutionContext` with:
- `token_id`: Groups related tasks (becomes `context_id`)
- `user_id`: User who submitted the group

When a task with a context is dequeued, ALL pending tasks with the same `context_id` are dequeued and executed as a batch. This ensures atomic execution without interleaving.

**Execution Flow:**
```
executor.execute(task, user) →
  queue.enqueue(task) →
    main loop: executor._execute_next() →
      hwman.run_circuit(gates, shots) →
        Physical QPU
```

### SLURM Integration

**Two-Layer User Interaction Model:**

1. **Layer 1: SLURM (Resource Allocation)**
   - Users submit jobs: `sbatch --gres=qpu:1 my_quantum_script.sh`
   - SLURM decides who gets QPU access and when
   - Partition: `qpu` on node `qpu-node01`

2. **Layer 2: LCCFQ Backend (Task Execution)**
   - Once allocated, user's job script calls backend gRPC API to submit quantum tasks
   - Backend manages queue and executes on physical QPU

**Observable Export (`slurm/exporter.py`)**
- Exports QPU metrics to `/tmp/qpu_observables.env` in KEY=VALUE format
- Per-qubit metrics: frequency, T1, T2, gate fidelities, max circuit depth
- Called by watchdog, readable by SLURM for scheduling decisions

**Status Flag (`/tmp/qpu_status.flag`)**
- Contains: `"online"` or `"offline"`
- Written by: Watchdog every 300s
- Read by: Executor (execution gate) and SLURM (scheduling decisions)
- Determines if QPU is available for task execution

**Observable Environment (`/tmp/qpu_observables.env`)**
- Format: KEY=VALUE pairs (e.g., `Q0_FREQ=4.9`, `Q0_T1=30.0`)
- Written by: Watchdog via `slurm/exporter.py`
- Read by: SLURM jobs to know QPU capabilities

## gRPC API

### Protocol Buffers

**Proto Definition** (`src/lccfq_backend/api/protos/qpu_service.proto`):
- Defines the QPU Executor service
- Currently includes `Ping` RPC for testing connectivity
- Extensible for additional RPCs (task submission, status queries, etc.)

**Compiled Files** (`src/lccfq_backend/api/protobufs_compiled/`):
- Auto-generated from proto files using `make protos`
- Contains `qpu_service_pb2.py` and `qpu_service_pb2_grpc.py`

### mTLS Authentication

**Automatic Certificate Management:**

The gRPC server uses `CertificateManager` for automatic certificate generation. On first run, it creates:
- `certs/ca.crt` - Certificate Authority certificate (self-signed, valid for 10 years)
- `certs/ca.key` - CA private key (keep secure!)
- `certs/server.crt` - Server certificate (signed by CA, valid for 1 year)
- `certs/server.key` - Server private key
- `certs/clients/` - Directory for client certificates

**Certificate Details:**
- **CA Certificate**: Self-signed, marked as a CA (can sign other certificates)
- **Server Certificate**: Signed by CA, includes Subject Alternative Names (localhost, 127.0.0.1)
- **Client Certificates**: Signed by CA, marked for client authentication only
- The server requires mutual TLS - both client and server authenticate to each other

**Creating Client Certificates:**
```python
from lccfq_backend.api.certificates import CertificateManager

cert_manager = CertificateManager("./certs")
client_cert_file, client_key_file = cert_manager.create_client_certificate("user_id")
```

### Extending the gRPC API

To add new RPC methods:

1. **Update the proto file** (`src/lccfq_backend/api/protos/qpu_service.proto`):
   ```protobuf
   service QPUExecutor {
     rpc Ping(ExecutorRequest) returns (ExecutorResponse);
     rpc SubmitTask(TaskSubmissionRequest) returns (TaskSubmissionResponse);
   }
   ```

2. **Recompile protos**:
   ```bash
   make protos
   ```

3. **Implement in executor_service.py**:
   ```python
   def SubmitTask(self, request: TaskSubmissionRequest, context: grpc.ServicerContext) -> TaskSubmissionResponse:
       # Implementation
   ```

## Key Design Patterns

1. **Synchronous Execution**: The codebase was intentionally refactored to remove async/await. All operations are synchronous.

2. **State-First Design**: Always check and transition QPU state before operations. Invalid transitions raise `UnknownQPUState`.

3. **Context Locking**: When a task with a context is enqueued, that context is locked until all its tasks complete.

4. **Logging**: Use `setup_logger()` from `utils/log.py` for consistent logging. Loggers are named by module path.

5. **Task IDs**: Auto-generated UUIDs via `generate_task_id()`. Always use `task.task_id` for tracking.

6. **Error Handling**: Custom exceptions in `backend/error.py`: `UnknownQPUTaskType`, `QPUQueueEmpty`, `UnknownQPUState`.

7. **Thread Safety**: The executor instance is shared between the main loop thread and the gRPC server thread. The executor itself is not thread-safe by design (expects single-threaded operation). Care must be taken when adding new RPC methods that call executor methods.

## Testing

Test files are in `src/tests/` with structure mirroring `src/lccfq_backend/`:
- Unit tests for individual modules (queue, executor, FSM, etc.)
- Integration tests in `tests/integration/`
- Use pytest fixtures for common setups
- `TestTask` class has `__test__ = False` to prevent pytest collection

## Shutdown Sequence

When the service receives a termination signal (SIGTERM/SIGINT):

1. `shutdown_flag` is set to True
2. Main loop exits the polling loop
3. Watchdog thread is stopped
4. gRPC server is stopped gracefully via `cleanup()`
5. All resources are released

The daemon gRPC server thread will automatically terminate when the main thread exits.

## Dependencies

**Required Packages:**
- `grpcio>=1.66.0`
- `grpcio-tools>=1.66.0`
- Python 3.12+ required

These are automatically included in the project dependencies.

## Important Implementation Notes

- The hardware manager (`hwman.py`) currently returns mock data. Real hardware integration goes here.
- Main loop polls every 10 seconds by default, watchdog every 300 seconds
- Signal handling (SIGTERM, SIGINT) ensures graceful shutdown
- The watchdog runs as a daemon thread, stopped explicitly in shutdown sequence
- No manual certificate management required - fully self-contained on startup
- SLURM and backend are **separate services** communicating via files
- All operations are synchronous (no async/await)