#!/usr/bin/env python3
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from cryptography import x509
from dotenv import load_dotenv

from lccfq_backend.api.certificates.certificate_manager import CertificateManager
from lccfq_backend.config import BackendSettings
from lccfq_backend.main import main as run_backend
from lccfq_backend.utils.log import setup_logger

app = typer.Typer(
    name="backend",
    help="LCCFQ Backend CLI",
)

cert_app = typer.Typer(
    name="cert",
    help="Certificate management commands",
)


@app.command()
def start(
    config_file: Annotated[
        str, typer.Option("-c", "--config", help="Path to TOML configuration file")
    ] = "config.toml",
) -> None:
    """Start the LCCFQ backend service."""
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    config_path = Path(config_file)
    try:
        config = BackendSettings(_toml_file=config_path)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo(f"Please place a config file at {config_path}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        raise typer.Exit(1)

    os.environ["LCCFQ_LOG_LEVEL"] = config.log_level

    logger = setup_logger("lccfq.main")
    logger.info(f"Config file:  {config_path.absolute()}")
    logger.info(f"gRPC address: {config.grpc_address}:{config.grpc_port}")
    logger.info(f"Cert dir:     {config.cert_dir}")
    logger.info(f"Log level:    {config.log_level}")

    try:
        run_backend(config)
    except KeyboardInterrupt:
        raise typer.Exit(0)
    except Exception as e:
        logger.error(f"Server failed: {e}")
        raise typer.Exit(1)


@cert_app.command("setup-server")
def cert_setup_server(
    cert_dir: Annotated[
        str, typer.Option("--cert-dir", help="Certificate directory")
    ] = "./certs",
    hostname: Annotated[
        str, typer.Option("--hostname", help="Server hostname")
    ] = "localhost",
) -> None:
    """Set up CA and server certificates."""
    typer.echo(f"Setting up server certificates in: {cert_dir}")
    cert_manager = CertificateManager(Path(cert_dir))
    ca_cert_file, server_cert_file, server_key_file = cert_manager.setup_ca_and_server(hostname)
    typer.echo("Server certificate setup complete!")
    typer.echo(f"  CA certificate:   {ca_cert_file}")
    typer.echo(f"  Server certificate: {server_cert_file}")
    typer.echo(f"  Server private key: {server_key_file}")
    typer.echo("\nNext steps:")
    typer.echo("  Start the server: uv run backend start")


@cert_app.command("create-client")
def cert_create_client(
    user_id: Annotated[str, typer.Argument(help="User ID for the certificate")],
    cert_dir: Annotated[
        str, typer.Option("--cert-dir", help="Certificate directory")
    ] = "./certs",
) -> None:
    """Create a client certificate for a specific user."""
    cert_manager = CertificateManager(Path(cert_dir))

    if not (cert_manager.ca_cert_file.exists() and cert_manager.server_cert_file.exists()):
        typer.echo("Error: Server certificates not found.", err=True)
        typer.echo("Run setup-server first: uv run backend cert setup-server", err=True)
        raise typer.Exit(1)

    try:
        client_cert_file, client_key_file = cert_manager.create_client_certificate(user_id)
        typer.echo(f"Client certificate created for user: {user_id}")
        typer.echo(f"  Certificate: {client_cert_file}")
        typer.echo(f"  Private key: {client_key_file}")
        typer.echo("\nCertificate details:")
        _display_certificate_info(client_cert_file)
    except Exception as e:
        typer.echo(f"Failed to create client certificate: {e}", err=True)
        raise typer.Exit(1)


@cert_app.command("list-clients")
def cert_list_clients(
    cert_dir: Annotated[
        str, typer.Option("--cert-dir", help="Certificate directory")
    ] = "./certs",
) -> None:
    """List all existing client certificates."""
    cert_manager = CertificateManager(Path(cert_dir))
    clients = cert_manager.list_client_certificates()

    if not clients:
        typer.echo("No client certificates found.")
        typer.echo("Create one with: uv run backend cert create-client <user_id>")
        return

    typer.echo(f"Found {len(clients)} client certificate(s):")
    for user_id, (cert_path, key_path) in clients.items():
        typer.echo(f"\nUser: {user_id}")
        typer.echo(f"  Certificate: {cert_path}")
        typer.echo(f"  Private key: {key_path}")
        try:
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            now = datetime.now(timezone.utc)
            expires = cert.not_valid_after_utc
            if expires > now:
                typer.echo(f"  Status: Valid (expires in {(expires - now).days} days)")
            else:
                typer.echo("  Status: Expired")
        except Exception as e:
            typer.echo(f"  Status: Could not read certificate: {e}")


@cert_app.command("status")
def cert_status(
    cert_dir: Annotated[
        str, typer.Option("--cert-dir", help="Certificate directory")
    ] = "./certs",
) -> None:
    """Display the status of server certificates."""
    cert_manager = CertificateManager(Path(cert_dir))

    typer.echo(f"Server Certificate Status ({cert_dir}):")
    typer.echo("")

    if cert_manager.ca_cert_file.exists():
        typer.echo(f"CA Certificate: {cert_manager.ca_cert_file}")
        _display_certificate_info(cert_manager.ca_cert_file)
    else:
        typer.echo(f"CA Certificate missing: {cert_manager.ca_cert_file}")

    typer.echo("")

    if cert_manager.server_cert_file.exists():
        typer.echo(f"Server Certificate: {cert_manager.server_cert_file}")
        _display_certificate_info(cert_manager.server_cert_file)
    else:
        typer.echo(f"Server Certificate missing: {cert_manager.server_cert_file}")

    typer.echo("")

    if cert_manager.ca_cert_file.exists() and cert_manager.server_cert_file.exists():
        typer.echo("Server certificates are ready.")
        typer.echo("Start the server with: uv run backend start")
    else:
        typer.echo("Server certificates are incomplete.")
        typer.echo("Run: uv run backend cert setup-server")


def _display_certificate_info(cert_file: Path) -> None:
    try:
        with open(cert_file, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())

        user_id = None
        for attribute in cert.subject:
            if attribute.oid == x509.oid.NameOID.COMMON_NAME:
                user_id = attribute.value
                break

        now = datetime.now(timezone.utc)
        expires = cert.not_valid_after_utc
        days_left = (expires - now).days

        typer.echo(f"  CN: {user_id}")
        typer.echo(f"  Valid from:  {cert.not_valid_before_utc}")
        typer.echo(f"  Valid until: {expires}")
        if expires > now:
            typer.echo(f"  Status: Valid ({days_left} days remaining)")
        else:
            typer.echo("  Status: Expired")
    except Exception as e:
        typer.echo(f"  Could not read certificate: {e}")


app.add_typer(cert_app, name="cert")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
