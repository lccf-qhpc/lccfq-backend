import pytest
from lccfq_backend.backend.users import UserManager
from lccfq_backend.model.user import User, Permissions


@pytest.fixture
def manager():
    return UserManager()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def test_create_user(manager):
    user = manager.create_user("alice")
    assert user.name == "alice"
    assert user.perms == Permissions(0)
    assert manager.has_user("alice")


def test_create_user_with_perms(manager):
    user = manager.create_user("bob", Permissions.SUBMIT_CIRCUITS)
    assert user.perms == Permissions.SUBMIT_CIRCUITS


def test_has_user_false(manager):
    assert not manager.has_user("nobody")


def test_get_user(manager):
    manager.create_user("alice")
    assert manager.get_user("alice").name == "alice"


def test_add_user(manager):
    manager.add_user(User(id=1, name="carol"))
    assert manager.has_user("carol")


# ---------------------------------------------------------------------------
# User permissions
# ---------------------------------------------------------------------------

def test_add_permission(manager):
    manager.create_user("alice")
    manager.add_permission("alice", Permissions.SUBMIT_CIRCUITS)
    assert manager.check_permission("alice", Permissions.SUBMIT_CIRCUITS)


def test_add_multiple_permissions(manager):
    manager.create_user("alice")
    manager.add_permission("alice", Permissions.SUBMIT_CIRCUITS)
    manager.add_permission("alice", Permissions.RESET)
    assert manager.check_permission("alice", Permissions.SUBMIT_CIRCUITS)
    assert manager.check_permission("alice", Permissions.RESET)


def test_remove_permission(manager):
    manager.create_user("alice", Permissions.SUBMIT_CIRCUITS)
    manager.remove_permission("alice", Permissions.SUBMIT_CIRCUITS)
    assert not manager.check_permission("alice", Permissions.SUBMIT_CIRCUITS)


def test_remove_permission_leaves_others(manager):
    manager.create_user("alice", Permissions.SUBMIT_CIRCUITS | Permissions.RESET)
    manager.remove_permission("alice", Permissions.RESET)
    assert manager.check_permission("alice", Permissions.SUBMIT_CIRCUITS)
    assert not manager.check_permission("alice", Permissions.RESET)


def test_add_permission_nonexistent_user(manager):
    with pytest.raises(ValueError):
        manager.add_permission("ghost", Permissions.SUBMIT_CIRCUITS)


def test_remove_permission_nonexistent_user(manager):
    with pytest.raises(ValueError):
        manager.remove_permission("ghost", Permissions.SUBMIT_CIRCUITS)


def test_check_permission_nonexistent_user(manager):
    assert not manager.check_permission("nobody", Permissions.SUBMIT_CIRCUITS)


def test_check_permission_no_permission(manager):
    manager.create_user("alice")
    assert not manager.check_permission("alice", Permissions.SUBMIT_CIRCUITS)


def test_check_permission_via_group(manager):
    manager.create_user("alice")
    manager.create_group("admins", Permissions.RESET)
    manager.add_user_to_group("alice", "admins")
    assert manager.check_permission("alice", Permissions.RESET)


def test_check_permission_not_in_group(manager):
    manager.create_user("alice")
    manager.create_group("admins", Permissions.RESET)
    assert not manager.check_permission("alice", Permissions.RESET)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

def test_create_group(manager):
    group = manager.create_group("admins")
    assert group.name == "admins"
    assert manager.has_group("admins")


def test_create_group_with_perms(manager):
    group = manager.create_group("ops", Permissions.RESET)
    assert group.perms == Permissions.RESET


def test_has_group_false(manager):
    assert not manager.has_group("nobody")


def test_get_group(manager):
    manager.create_group("admins")
    assert manager.get_group("admins").name == "admins"


def test_remove_group(manager):
    manager.create_group("admins")
    manager.remove_group("admins")
    assert not manager.has_group("admins")


def test_remove_group_removes_from_users(manager):
    manager.create_user("alice")
    manager.create_group("admins")
    manager.add_user_to_group("alice", "admins")
    manager.remove_group("admins")
    assert len(manager.get_user("alice").groups) == 0


def test_remove_group_removes_from_multiple_users(manager):
    manager.create_user("alice")
    manager.create_user("bob")
    manager.create_group("admins")
    manager.add_user_to_group("alice", "admins")
    manager.add_user_to_group("bob", "admins")
    manager.remove_group("admins")
    assert len(manager.get_user("alice").groups) == 0
    assert len(manager.get_user("bob").groups) == 0


def test_remove_group_only_removes_target_group(manager):
    manager.create_user("alice")
    manager.create_group("admins")
    manager.create_group("users")
    manager.add_user_to_group("alice", "admins")
    manager.add_user_to_group("alice", "users")
    manager.remove_group("admins")
    alice = manager.get_user("alice")
    assert len(alice.groups) == 1
    assert alice.groups[0].name == "users"


def test_remove_nonexistent_group(manager):
    with pytest.raises(ValueError):
        manager.remove_group("ghost")


# ---------------------------------------------------------------------------
# Group membership
# ---------------------------------------------------------------------------

def test_add_user_to_group(manager):
    manager.create_user("alice")
    manager.create_group("admins")
    manager.add_user_to_group("alice", "admins")
    user = manager.get_user("alice")
    assert any(g.name == "admins" for g in user.groups)


def test_add_user_to_group_idempotent(manager):
    manager.create_user("alice")
    manager.create_group("admins")
    manager.add_user_to_group("alice", "admins")
    manager.add_user_to_group("alice", "admins")
    assert len(manager.get_user("alice").groups) == 1


def test_remove_user_from_group(manager):
    manager.create_user("alice")
    manager.create_group("admins")
    manager.add_user_to_group("alice", "admins")
    manager.remove_user_from_group("alice", "admins")
    assert len(manager.get_user("alice").groups) == 0


def test_remove_user_not_in_group_is_noop(manager):
    manager.create_user("alice")
    manager.create_group("admins")
    manager.remove_user_from_group("alice", "admins")  # should not raise
    assert len(manager.get_user("alice").groups) == 0


def test_add_user_to_group_nonexistent_user(manager):
    manager.create_group("admins")
    with pytest.raises(ValueError):
        manager.add_user_to_group("ghost", "admins")


def test_add_user_to_group_nonexistent_group(manager):
    manager.create_user("alice")
    with pytest.raises(ValueError):
        manager.add_user_to_group("alice", "ghost")


def test_remove_user_from_group_nonexistent_user(manager):
    manager.create_group("admins")
    with pytest.raises(ValueError):
        manager.remove_user_from_group("ghost", "admins")


def test_remove_user_from_group_nonexistent_group(manager):
    manager.create_user("alice")
    with pytest.raises(ValueError):
        manager.remove_user_from_group("alice", "ghost")


# ---------------------------------------------------------------------------
# Group permissions
# ---------------------------------------------------------------------------

def test_add_group_permission(manager):
    manager.create_group("admins")
    manager.add_group_permission("admins", Permissions.RESET)
    assert manager.get_group("admins").perms & Permissions.RESET


def test_add_multiple_group_permissions(manager):
    manager.create_group("admins")
    manager.add_group_permission("admins", Permissions.RESET)
    manager.add_group_permission("admins", Permissions.RETUNE)
    g = manager.get_group("admins")
    assert g.perms & Permissions.RESET
    assert g.perms & Permissions.RETUNE


def test_remove_group_permission(manager):
    manager.create_group("admins", Permissions.RESET)
    manager.remove_group_permission("admins", Permissions.RESET)
    assert not (manager.get_group("admins").perms & Permissions.RESET)


def test_remove_group_permission_leaves_others(manager):
    manager.create_group("admins", Permissions.RESET | Permissions.RETUNE)
    manager.remove_group_permission("admins", Permissions.RESET)
    g = manager.get_group("admins")
    assert not (g.perms & Permissions.RESET)
    assert g.perms & Permissions.RETUNE


def test_add_group_permission_nonexistent(manager):
    with pytest.raises(ValueError):
        manager.add_group_permission("ghost", Permissions.RESET)


def test_remove_group_permission_nonexistent(manager):
    with pytest.raises(ValueError):
        manager.remove_group_permission("ghost", Permissions.RESET)


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------

def test_round_trip_empty(manager, tmp_path):
    path = tmp_path / "users.json"
    manager.load_to_file(path)
    loaded = UserManager()
    loaded.load_from_file(path)
    assert loaded.users == {}
    assert loaded.groups == {}


def test_round_trip_users_only(manager, tmp_path):
    path = tmp_path / "users.json"
    manager.create_user("alice", Permissions.SUBMIT_CIRCUITS)
    manager.create_user("bob")
    manager.load_to_file(path)

    loaded = UserManager()
    loaded.load_from_file(path)
    assert loaded.has_user("alice")
    assert loaded.get_user("alice").perms == Permissions.SUBMIT_CIRCUITS
    assert loaded.has_user("bob")


def test_round_trip_groups_only(manager, tmp_path):
    path = tmp_path / "users.json"
    manager.create_group("admins", Permissions.RESET)
    manager.load_to_file(path)

    loaded = UserManager()
    loaded.load_from_file(path)
    assert loaded.has_group("admins")
    assert loaded.get_group("admins").perms == Permissions.RESET


def test_round_trip_users_and_groups(manager, tmp_path):
    path = tmp_path / "users.json"
    manager.create_group("admins", Permissions.RESET)
    manager.create_user("alice", Permissions.SUBMIT_CIRCUITS)
    manager.add_user_to_group("alice", "admins")
    manager.load_to_file(path)

    loaded = UserManager()
    loaded.load_from_file(path)
    assert loaded.has_user("alice")
    assert loaded.has_group("admins")
    alice = loaded.get_user("alice")
    assert alice.perms == Permissions.SUBMIT_CIRCUITS
    assert any(g.name == "admins" for g in alice.groups)
    assert loaded.get_group("admins").perms == Permissions.RESET


def test_round_trip_group_permission_check(manager, tmp_path):
    path = tmp_path / "users.json"
    manager.create_group("ops", Permissions.RESET)
    manager.create_user("alice")
    manager.add_user_to_group("alice", "ops")
    manager.load_to_file(path)

    loaded = UserManager()
    loaded.load_from_file(path)
    assert loaded.check_permission("alice", Permissions.RESET)


def test_round_trip_user_no_groups(manager, tmp_path):
    path = tmp_path / "users.json"
    manager.create_user("alice")
    manager.load_to_file(path)

    loaded = UserManager()
    loaded.load_from_file(path)
    assert loaded.get_user("alice").groups == []
