"""
Filename: users.py
Author: Owen Cochell
Date: 2026-04-07
Version: 1.0
Description:
    Tools for reading and writing user information, including permissions and group membership.
License: Apache 2.0
"""

from __future__ import annotations

import json
import pathlib

from ..model.user import User, Group, Permissions


class UserManager:
    """
    Manages users and their permissions.

    TODO:
    As of now, we trust the username provided by the client.
    In the future we may want to implement authentication and authorization mechanisms to verify user identities and permissions,
    likely on the gRPC side.
    """

    def __init__(self):

        self.users: dict[str, User] = {}  # Collection of users
        self.groups: dict[str, Group] = {}  # Collection of groups

    def load_to_file(self, file_path: pathlib.Path):
        """Save user information to a JSON file.

        :param file_path: The path to the JSON file to save user information to.
        """

        # Use the pydantic model's built in JSON serialization for users, and a custom serialization for groups

        data = {
            'groups': [
                group.model_dump()
                for group in self.groups.values()
            ],
            'users': [
                {**user.model_dump(exclude={'groups'}), 'groups': [g.name for g in user.groups]}
                for user in self.users.values()
            ]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def load_from_file(self, file_path: pathlib.Path):
        """Load user information from a JSON file.

        :param file_path: The path to the JSON file containing user information.
        """
        # Load the JSON data from the file

        with open(file_path, 'r') as f:
            data = json.load(f)

        # Load each group first

        for group_data in data.get('groups', []):
            group = Group.model_validate(group_data)
            self.groups[group.name] = group

        # Load each user and their respective groups

        for user_data in data.get('users', []):
            user_groups = [self.groups[g_name] for g_name in user_data.get('groups', [])]
            user = User.model_validate({**user_data, 'groups': user_groups})
            self.users[user.name] = user

    def add_user(self, user: User):
        """Add a user to the system.

        :param user: The user to add.
        """
        self.users[user.name] = user

    def has_user(self, name: str) -> bool:
        """Check if a user exists.

        :param name: The name of the user to check.
        :return: True if the user exists, False otherwise.
        """
        return name in self.users

    def get_user(self, name: str) -> User:
        """Get a user by name.

        :param name: The name of the user to get.
        :return: The user with the given name.
        """
        return self.users[name]

    def create_user(self, name: str, perms: Permissions = Permissions(0)) -> User:
        """Create a new user.

        :param name: The name of the user to create.
        :param perms: The permissions for the user.
        :return: The newly created user.
        """
        # TODO: Hardcoded ID
        user = User(name=name, perms=perms, id=0)
        self.add_user(user)
        return user

    def add_permission(self, user_name: str, permission: Permissions):
        """Add a permission to a user.

        :param user_name: The name of the user to add the permission to.
        :param permission: The permission to add.
        """
        if not self.has_user(user_name):
            raise ValueError(f"User '{user_name}' does not exist.")

        user = self.get_user(user_name)
        user.perms |= permission

    def remove_permission(self, user_name: str, permission: Permissions):
        """Remove a permission from a user.

        :param user_name: The name of the user to remove the permission from.
        :param permission: The permission to remove.
        """
        if not self.has_user(user_name):
            raise ValueError(f"User '{user_name}' does not exist.")

        user = self.get_user(user_name)
        user.perms &= ~permission

    def check_permission(self, user_name: str, permission: Permissions) -> bool:
        """Check if a user has a specific permission.

        :param user_name: The name of the user to check.
        :param permission: The permission to check for.
        :return: True if the user has the permission, False otherwise.
        """
        if not self.has_user(user_name):
            return False

        user = self.get_user(user_name)

        # Check direct permissions
        if user.perms & permission:
            return True

        # Check group permissions
        for group in user.groups:
            if group.perms & permission:
                return True

        return False

    def get_group(self, name: str) -> Group:
        """Get a group by name.

        :param name: The name of the group to get.
        :return: The group with the given name.
        """
        return self.groups[name]
    
    def has_group(self, name: str) -> bool:
        """Check if a group exists.

        :param name: The name of the group to check.
        :return: True if the group exists, False otherwise.
        """
        return name in self.groups
    
    def create_group(self, name: str, perms: Permissions = Permissions(0)) -> Group:
        """Create a new group.

        :param name: The name of the group to create.
        :param perms: The permissions for the group.
        :return: The newly created group.
        """

        group = Group(name=name, perms=perms, id=0)
        self.groups[group.name] = group
        return group

    def remove_group(self, name: str):
        """Remove a group.

        :param name: The name of the group to remove.
        """
        if not self.has_group(name):
            raise ValueError(f"Group '{name}' does not exist.")

        group = self.groups.pop(name)

        # Also remove this group from any users that are part of it

        for user in self.users.values():
            if group in user.groups:
                user.groups.remove(group)

    def add_user_to_group(self, user_name: str, group_name: str):
        """Add a user to a group.

        :param user_name: The name of the user to add to the group.
        :param group_name: The name of the group to add the user to.
        """
        if not self.has_user(user_name):
            raise ValueError(f"User '{user_name}' does not exist.")
        if not self.has_group(group_name):
            raise ValueError(f"Group '{group_name}' does not exist.")

        user = self.get_user(user_name)
        group = self.get_group(group_name)

        if group not in user.groups:
            user.groups.append(group)

    def remove_user_from_group(self, user_name: str, group_name: str):
        """Remove a user from a group.

        :param user_name: The name of the user to remove from the group.
        :param group_name: The name of the group to remove the user from.
        """
        if not self.has_user(user_name):
            raise ValueError(f"User '{user_name}' does not exist.")
        if not self.has_group(group_name):
            raise ValueError(f"Group '{group_name}' does not exist.")

        user = self.get_user(user_name)
        group = self.get_group(group_name)

        if group in user.groups:
            user.groups.remove(group)

    def add_group_permission(self, group_name: str, permission: Permissions):
        """Add a permission to a group.

        :param group_name: The name of the group to add the permission to.
        :param permission: The permission to add.
        """
        if not self.has_group(group_name):
            raise ValueError(f"Group '{group_name}' does not exist.")

        group = self.get_group(group_name)
        group.perms |= permission

    def remove_group_permission(self, group_name: str, permission: Permissions):
        """Remove a permission from a group.

        :param group_name: The name of the group to remove the permission from.
        :param permission: The permission to remove.
        """
        if not self.has_group(group_name):
            raise ValueError(f"Group '{group_name}' does not exist.")

        group = self.get_group(group_name)
        group.perms &= ~permission
