"""Configuration management for lccfq-backend using Pydantic Settings."""

import logging
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

logger = logging.getLogger(__name__)


class BackendSettings(BaseSettings):
    """Main configuration for lccfq-backend loaded from TOML file."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # Logging settings
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # Watchdog settings
    with_watchdog: bool = Field(
        default=True, description="Enable watchdog daemon for QPU health monitoring"
    )
    watchdog_interval: int = Field(
        default=300, description="Watchdog check interval in seconds"
    )

    # gRPC server settings
    with_grpc: bool = Field(
        default=True, description="Enable gRPC server for external API"
    )
    grpc_address: str = Field(
        default="[::]", description="gRPC server address to bind to ([::] = all IPv4/IPv6)"
    )
    grpc_port: int = Field(default=50052, description="gRPC server port")
    grpc_max_workers: int = Field(
        default=10, description="Maximum number of gRPC worker threads"
    )
    cert_dir: Path = Field(
        default=Path("./certs"), description="Directory for mTLS certificates"
    )

    # Hardware manager client settings
    hwman_mock_mode: bool = Field(
        default=True,
        description="Use mock hardware manager (for testing without real QPU)",
    )
    hwman_address: str = Field(
        default="localhost",
        description="Hardware manager gRPC server address",
    )
    hwman_port: int = Field(
        default=50222, description="Hardware manager gRPC server port"
    )
    hwman_cert_dir: Path = Field(
        default=Path("./certs"),
        description="Directory containing hwman client certificates",
    )
    hwman_cert_client_dir: Path = Field(
        default=Path("./certs/client"),
        description="Directory containing hwman client TLS certificates",
    )
    hwman_client_name: str = Field(
        default="backend_client",
        description="Client name for hwman authentication",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log level '{v}'. Must be one of: {', '.join(valid_levels)}"
            )
        return v.upper()

    @field_validator("watchdog_interval")
    @classmethod
    def validate_watchdog_interval(cls, v: int) -> int:
        """Validate watchdog interval is positive."""
        if v <= 0:
            raise ValueError(f"Watchdog interval must be positive, got {v}")
        return v

    @field_validator("grpc_port", "hwman_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type["BaseSettings"],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources to load from TOML file.

        This method implements the Pydantic settings sources API to support loading
        configuration from a TOML file. It prioritizes init_settings (which can pass
        a custom toml file path via _toml_file) over the TOML file source.

        Priority order (highest to lowest):
        1. Constructor arguments (init_settings)
        2. TOML config file
        3. Environment variables
        4. .env file
        5. File-based secrets
        """
        # Get the TOML file path from init_settings if provided (_toml_file),
        # otherwise use default
        init_data = init_settings() if callable(init_settings) else {}
        toml_path = init_data.get("_toml_file") or Path("config.toml")

        # Only create TomlConfigSettingsSource if the file exists
        toml_source = None
        if Path(toml_path).exists():
            toml_source = TomlConfigSettingsSource(settings_cls, str(toml_path))
            logger.info(f"Loading configuration from {toml_path}")
        else:
            logger.info(f"Config file {toml_path} not found, using defaults")

        # Build sources in priority order (higher priority = checked first)
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,  # Highest priority - constructor arguments
        ]

        if toml_source:
            sources.append(toml_source)

        sources.extend([
            env_settings,  # Environment variables
            dotenv_settings,  # .env file
            file_secret_settings,  # File-based secrets
        ])

        return tuple(sources)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary (useful for logging).

        Returns:
            Dictionary representation
        """
        return self.model_dump(mode="python")


# Singleton config instance - single source of truth for the entire application
config = BackendSettings()