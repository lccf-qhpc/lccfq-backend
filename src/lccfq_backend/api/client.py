from pathlib import Path

import grpc

from lccfq_backend.api.certificates.certificate_manager import CertificateManager
from lccfq_backend.utils.log import setup_logger
from lccfq_backend.api.protobufs_compiled.qpu_service_pb2_grpc import QPUExecutorStub
from lccfq_backend.api.protobufs_compiled.qpu_service_pb2 import (
    ExecutorResponse,
    ExecutorRequest,
    SubmitCircuitTaskRequest,
    SubmitCircuitTaskResponse,
    Gate as ProtoGate,
)
from lccfq_backend.model.tasks import Gate

logger = setup_logger("GRPCServer")


class Client:
    def __init__(self,
                 name: str,
                 address: str = "localhost",
                 port: int = 50052,
                 clients_cert_dir: str | Path = "./certs/clients",
                 server_cert_dir: str | Path = "./certs/ca.crt",
                 ):

        self.name = name
        self.address = address
        self.port = port

        self.ca_cert_path = Path(server_cert_dir)
        self.client_cert_path = Path(clients_cert_dir) / f"{self.name}.crt"
        self.client_key_path = Path(clients_cert_dir) / f"{self.name}.key"
        self.clients_cert_dir = Path(clients_cert_dir)


        self.ca_cert: bytes | None = None
        self.client_cert: bytes | None = None
        self.client_key: bytes | None = None

        self.executor_stub: QPUExecutorStub | None = None

        self._initialize_certificates()

        self.channel = None
        self.credentials = None

        self.initialize()

    def _initialize_certificates(self) -> None:
        if not self.ca_cert_path.exists():
            logger.error(f"CA certificate file not found: {self.ca_cert_path}")
            raise FileNotFoundError(
                f"CA certificate file not found: {self.ca_cert_path}"
            )

        if not self.client_cert_path.exists() or not self.client_key_path.exists():
            logger.info(
                f"Certificates files not found for client creating them: {self.client_cert_path}, {self.client_key_path}"
            )

            self.certificate_manager = CertificateManager(self.ca_cert_path.parent)
            self.certificate_manager.create_client_certificate(self.name)

        try:
            with open(self.ca_cert_path, "rb") as f:
                self.ca_cert = f.read()
        except FileNotFoundError as e:
            logger.error(f"CA certificate file not found: {self.ca_cert_path}")
            raise e
        try:
            with open(self.client_cert_path, "rb") as f:
                self.client_cert = f.read()
        except FileNotFoundError as e:
            logger.error(f"Client certificate file not found: {self.client_cert_path}")
            raise e
        try:
            with open(self.client_key_path, "rb") as f:
                self.client_key = f.read()
        except FileNotFoundError as e:
            logger.error(f"Client key file not found: {self.client_key_path}")
            raise e

    def initialize(self) -> None:
        logger.info(f"Initializing {self.name} client to secure channel {self.address}:{self.port}")

        self.credentials = grpc.ssl_channel_credentials(
            root_certificates=self.ca_cert,
            private_key=self.client_key,
            certificate_chain=self.client_cert,
        )

        self.channel = grpc.secure_channel(
            f"{self.address}:{self.port}",
            self.credentials
        )

        self.executor_stub = QPUExecutorStub(self.channel)
        logger.info(f"{self.name} client initialized successfully.")

    def ping(self) -> ExecutorResponse:
        try:
            assert self.executor_stub is not None, "Executor stub is not initialized."
            response = self.executor_stub.Ping(ExecutorRequest(message="Ping from client"))
            return response
        except grpc.RpcError as e:
            logger.error(f"gRPC error during Ping")
            raise e

    def submit_circuit_task(
        self,
        gates: list[Gate],
        shots: int
    ) -> SubmitCircuitTaskResponse:
        """
        Submit a circuit task to the QPU executor.

        Args:
            gates: List of Gate objects defining the quantum circuit
            shots: Number of measurement shots to perform

        Returns:
            SubmitCircuitTaskResponse with task_id and status

        Raises:
            grpc.RpcError: If the RPC call fails
            AssertionError: If executor_stub is not initialized
        """
        try:
            assert self.executor_stub is not None, "Executor stub is not initialized."

            # Convert Python Gate objects to proto Gates
            proto_gates = [
                ProtoGate(
                    symbol=g.symbol,
                    target_qubits=g.target_qubits,
                    control_qubits=g.control_qubits,
                    params=g.params,
                )
                for g in gates
            ]

            # Create request
            request = SubmitCircuitTaskRequest(
                gates=proto_gates,
                shots=shots
            )

            # Make RPC call
            logger.info(f"Submitting circuit task with {len(gates)} gates, {shots} shots")
            response = self.executor_stub.SubmitCircuitTask(request)

            if response.success:
                logger.info(f"Circuit task submitted successfully: {response.task_id}")
            else:
                logger.error(f"Circuit task submission failed: {response.message}")

            return response

        except grpc.RpcError as e:
            logger.error(f"gRPC error during SubmitCircuitTask: {e.code()} - {e.details()}")
            raise e
