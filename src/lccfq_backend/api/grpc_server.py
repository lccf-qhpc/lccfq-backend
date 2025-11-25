"""
gRPC Server for LCCFQ Backend with mTLS support.
Handles incoming gRPC requests from clients.
"""
from pathlib import Path
from concurrent import futures

import grpc

from lccfq_backend.api.protobufs_compiled import qpu_service_pb2_grpc
from lccfq_backend.api.services.executor_service import ExecutorService
from lccfq_backend.backend.executor import QPUExecutor
from lccfq_backend.api.certificates import CertificateManager
from lccfq_backend.utils.log import setup_logger

logger = setup_logger("GRPCServer")


class GRPCServer:
    """gRPC Server with mTLS support for LCCFQ Backend."""

    def __init__(
        self,
        executor: QPUExecutor,
        address: str = "[::]",
        port: int = 50052,
        cert_dir: str | Path = "./certs",
    ):
        """
        Initialize the gRPC Server.

        Args:
            executor: QPUExecutor instance to handle requests
            address: Address to bind to (default: all interfaces)
            port: Port to listen on (default: 50052)
            cert_dir: Directory containing certificates for mTLS
        """
        self.executor = executor
        self.address = address
        self.port = port
        self.cert_dir = Path(cert_dir)

        self.server_cert: bytes | None = None
        self.server_key: bytes | None = None
        self.ca_cert: bytes | None = None

        self.executor_service: ExecutorService | None = None
        self.server: grpc.Server | None = None

        logger.info(f"GRPCServer initialized (address: {address}:{port})")

    def _initialize_certificates(self) -> None:
        """Initialize mTLS certificates using CertificateManager."""
        logger.info("Initializing certificates for mTLS...")

        # Use CertificateManager to set up certificates
        cert_manager = CertificateManager(self.cert_dir)
        ca_cert_file, server_cert_file, server_key_file = cert_manager.setup_ca_and_server()

        # Load certificate files
        try:
            with open(server_cert_file, "rb") as f:
                self.server_cert = f.read()
            logger.debug(f"Loaded server certificate from {server_cert_file}")
        except FileNotFoundError as e:
            logger.error(f"Server certificate file not found: {server_cert_file}")
            raise e

        try:
            with open(server_key_file, "rb") as f:
                self.server_key = f.read()
            logger.debug(f"Loaded server key from {server_key_file}")
        except FileNotFoundError as e:
            logger.error(f"Server key file not found: {server_key_file}")
            raise e

        try:
            with open(ca_cert_file, "rb") as f:
                self.ca_cert = f.read()
            logger.debug(f"Loaded CA certificate from {ca_cert_file}")
        except FileNotFoundError as e:
            logger.error(f"CA certificate file not found: {ca_cert_file}")
            raise e

        logger.info("Certificates initialized successfully.")

    def _initialize_services(self) -> None:
        """Initialize and register gRPC services."""
        logger.info("Initializing executor service...")
        self.executor_service = ExecutorService(self.executor)
        qpu_service_pb2_grpc.add_QPUExecutorServicer_to_server(
            self.executor_service, self.server
        )
        logger.info("Executor service initialized and registered.")

    def serve(self) -> None:
        """Start the gRPC server and wait for termination."""
        try:
            logger.info(f"Starting gRPC server on {self.address}:{self.port}")

            # Initialize certificates
            self._initialize_certificates()

            # Create server with thread pool
            self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

            # Set up mTLS
            server_credentials = grpc.ssl_server_credentials(
                private_key_certificate_chain_pairs=[
                    (self.server_key, self.server_cert)
                ],
                root_certificates=self.ca_cert,
                require_client_auth=True,
            )

            logger.info("Server instantiated with mTLS channel.")
            self.server.add_secure_port(f"{self.address}:{self.port}", server_credentials)
            logger.info(f"Secure port added: {self.address}:{self.port}")

            # Initialize and register services
            self._initialize_services()

            # Start server
            logger.info("Starting gRPC server...")
            self.server.start()
            logger.info("gRPC server started successfully.")

            # Wait for termination
            self.server.wait_for_termination()

        except KeyboardInterrupt:
            logger.info("Server stopped by user.")
        except Exception as e:
            logger.error(f"Server stopped with error: {e}")
            raise e
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up server resources."""
        logger.info("Cleaning up server resources.")
        if self.server:
            self.server.stop(0)
            self.server = None
        logger.info("Server resources cleaned up successfully.")