"""
gRPC service implementation for QPU Executor.
Wraps the executor instance to handle incoming gRPC requests.
"""

import grpc

from lccfq_backend.api.protobufs_compiled.qpu_service_pb2_grpc import QPUExecutorServicer
from lccfq_backend.api.protobufs_compiled.qpu_service_pb2 import (
    ExecutorRequest,
    ExecutorResponse,
)
from lccfq_backend.backend.executor import QPUExecutor
from lccfq_backend.utils.log import setup_logger

logger = setup_logger("ExecutorService")


class ExecutorService(QPUExecutorServicer):
    """gRPC service that wraps the QPU Executor."""

    def __init__(self, executor: QPUExecutor):
        """
        Initialize the ExecutorService with an executor instance.

        Args:
            executor: QPUExecutor instance to use for handling requests
        """
        self.executor = executor
        logger.info("ExecutorService initialized with executor instance")

    def Ping(self, request: ExecutorRequest, context: grpc.ServicerContext) -> ExecutorResponse:
        """
        Handle the Ping request to check service health.

        Args:
            request: ExecutorRequest message
            context: gRPC service context

        Returns:
            ExecutorResponse with success status and message
        """
        logger.info(f"Received Ping request from client {context.peer()}")
        response = ExecutorResponse(
            message="Pong from LCCFQ Backend",
            success=True
        )
        return response