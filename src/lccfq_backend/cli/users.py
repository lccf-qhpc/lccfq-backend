"""
CLI commands for user management.
"""

import typer

from pathlib import Path
from typing import Annotated

from lccfq_backend.config import BackendSettings
from lccfq_backend.backend.users import UserManager
from lccfq_backend.model.user import Permissions

user_app = typer.Typer(
    name="user",
    help="User Management Commands",
)


def init_users(config_file: str):
    """Initialize the user management system
    """

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

    # Create and load the user manager

    user_manager = UserManager()

    try:

        user_manager.load_from_file(config.user_file)

    except Exception as e:
        typer.echo(f"Failed to load user data: {e}. Starting with empty user manager.", err=True)
    
    return user_manager, config

@user_app.command()
def add(name: str):
    """Add a new user with the given name.
    """

    user_manager, config = init_users(config_file="config.toml")

    try:

        user_manager.create_user(name=name, perms=Permissions(0))

        user_manager.load_to_file(config.user_file)

        typer.echo(f"User '{name}' added successfully.")
    except Exception as e:
        typer.echo(f"Error adding user: {e}", err=True)
        raise typer.Exit(1)

@user_app.command("list")
def list_user():
    """List all users.
    """

    user_manager, _ = init_users(config_file="config.toml")

    typer.echo("Users:")
    for user in user_manager.users:
        typer.echo(f"  - {user}")

@user_app.command()
def info(name: str):
    """Show information about a specific user.
    """

    user_manager, _ = init_users(config_file="config.toml")

    # Get the user from the manager

    user = user_manager.get_user(name)

    if user:
        typer.echo(f"User: {user.name}")
        typer.echo(f"  ID: {user.id}")
        typer.echo(f"  Permissions: {user.perms}")
        typer.echo(f"  Groups: {[group.name for group in user.groups]}")
    else:
        typer.echo(f"User '{name}' not found.", err=True)
        raise typer.Exit(1)

@user_app.command()
def list_perms():
    """List all available permissions.
    """

    typer.echo("Available Permissions:")
    for perm in Permissions:
        typer.echo(f"  - {perm.name} (value: {perm.value})")

@user_app.command()
def add_perms(name: str, perms: Annotated[list[Permissions], typer.Option()]):
    """Add permissions to a user.
    """

    user_manager, config = init_users(config_file="config.toml")

    # Does the user exist?

    if not user_manager.has_user(name):
        typer.echo(f"User '{name}' not found.", err=True)
        raise typer.Exit(1)

    # Add the specified permissions to the user

    for perm_name in perms:
        try:

            user_manager.add_permission(name, Permissions(perm_name))
        except KeyError:
            typer.echo(f"Permission '{perm_name}' not found.", err=True)
            raise typer.Exit(1)

    # Save the updated user manager

    user_manager.load_to_file(config.user_file)

    typer.echo(f"Permissions {perms} added to user '{name}' successfully.")


@user_app.command()
def remove_perms(name: str, perms: Annotated[list[Permissions], typer.Option()]):
    """Remove permissions from a user.
    """

    user_manager, config = init_users(config_file="config.toml")

    # Does the user exist?

    if not user_manager.has_user(name):
        typer.echo(f"User '{name}' not found.", err=True)
        raise typer.Exit(1)

    # Remove the specified permissions from the user

    for perm_name in perms:
        try:

            user_manager.remove_permission(name, Permissions(perm_name))
        except KeyError:
            typer.echo(f"Permission '{perm_name}' not found.", err=True)
            raise typer.Exit(1)

    # Save the updated user manager

    user_manager.load_to_file(config.user_file)

    typer.echo(f"Permissions {perms} removed from user '{name}' successfully.")


@user_app.command("glist")
def list_groups():
    """List all groups.
    """

    user_manager, _ = init_users(config_file="config.toml")

    typer.echo("Groups:")
    for group in user_manager.groups:
        typer.echo(f"  - {group}")


@user_app.command("ginfo")
def group_info(name: str):
    """Show information about a specific group.
    """

    user_manager, _ = init_users(config_file="config.toml")

    # Get the group from the manager

    group = user_manager.get_group(name)

    if group:
        typer.echo(f"Group: {group.name}")
        typer.echo(f"  ID: {group.id}")
        typer.echo(f"  Permissions: {group.perms}")
    else:
        typer.echo(f"Group '{name}' not found.", err=True)
        raise typer.Exit(1)


@user_app.command("gadd")
def add_group(name: str, perms: Annotated[list[Permissions], typer.Option()]):
    """Add a new group with the given name and permissions.
    """

    user_manager, config = init_users(config_file="config.toml")

    try:

        user_manager.create_group(name=name, perms=Permissions(0))

        for perm_name in perms:
            try:

                user_manager.add_group_permission(name, Permissions(perm_name))
            except KeyError:
                typer.echo(f"Permission '{perm_name}' not found.", err=True)
                raise typer.Exit(1)

        user_manager.load_to_file(config.user_file)

        typer.echo(f"Group '{name}' added successfully.")
    except Exception as e:
        typer.echo(f"Error adding group: {e}", err=True)
        raise typer.Exit(1)


@user_app.command()
def remove_group(name: str):
    """Remove a group.
    """

    user_manager, config = init_users(config_file="config.toml")

    # Does the group exist?

    if not user_manager.has_group(name):
        typer.echo(f"Group '{name}' not found.", err=True)
        raise typer.Exit(1)

    # Remove the group from the manager

    try:

        user_manager.remove_group(name)

        user_manager.load_to_file(config.user_file)

        typer.echo(f"Group '{name}' removed successfully.")
    except Exception as e:
        typer.echo(f"Error removing group: {e}", err=True)
        raise typer.Exit(1)


@user_app.command("gadd-perms")
def add_group_perms(name: str, perms: Annotated[list[Permissions], typer.Option()]):
    """Add permissions to a group.
    """

    user_manager, config = init_users(config_file="config.toml")

    # Does the group exist?

    if not user_manager.has_group(name):
        typer.echo(f"Group '{name}' not found.", err=True)
        raise typer.Exit(1)

    # Add the specified permissions to the group

    for perm_name in perms:
        try:

            user_manager.add_group_permission(name, Permissions(perm_name))
        except KeyError:
            typer.echo(f"Permission '{perm_name}' not found.", err=True)
            raise typer.Exit(1)

    # Save the updated user manager

    user_manager.load_to_file(config.user_file)

    typer.echo(f"Permissions {perms} added to group '{name}' successfully.")


@user_app.command("gremove-perms")
def remove_group_perms(name: str, perms: Annotated[list[Permissions], typer.Option()]):
    """Remove permissions from a group.
    """

    user_manager, config = init_users(config_file="config.toml")

    # Does the group exist?

    if not user_manager.has_group(name):
        typer.echo(f"Group '{name}' not found.", err=True)
        raise typer.Exit(1)

    # Remove the specified permissions from the group

    for perm_name in perms:
        try:

            user_manager.remove_group_permission(name, Permissions(perm_name))
        except KeyError:
            typer.echo(f"Permission '{perm_name}' not found.", err=True)
            raise typer.Exit(1)

    # Save the updated user manager

    user_manager.load_to_file(config.user_file)

    typer.echo(f"Permissions {perms} removed from group '{name}' successfully.")


@user_app.command("user-gadd")
def add_user_to_group(user_name: str, group_name: str):
    """Add a user to a group.
    """

    user_manager, config = init_users(config_file="config.toml")

    try:

        user_manager.add_user_to_group(user_name, group_name)

        user_manager.load_to_file(config.user_file)

        typer.echo(f"User '{user_name}' added to group '{group_name}' successfully.")
    except Exception as e:
        typer.echo(f"Error adding user to group: {e}", err=True)
        raise typer.Exit(1)
    

@user_app.command("user-gremove")
def remove_user_from_group(user_name: str, group_name: str):
    """Remove a user from a group.
    """

    user_manager, config = init_users(config_file="config.toml")

    try:

        user_manager.remove_user_from_group(user_name, group_name)

        user_manager.load_to_file(config.user_file)

        typer.echo(f"User '{user_name}' removed from group '{group_name}' successfully.")
    except Exception as e:
        typer.echo(f"Error removing user from group: {e}", err=True)
        raise typer.Exit(1)
