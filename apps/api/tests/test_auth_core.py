"""Tests for auth utilities — JWT, password hashing, role checks."""

import uuid

import pytest
from app.core.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from fastapi import HTTPException


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "my_secure_password"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_different_hashes_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def _make_user(self):
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
            email="jwt@test.com",
            full_name="JWT Test",
            role="analyst",
        )
        return user

    def test_create_and_decode(self):
        user = self._make_user()
        token = create_access_token(user)
        payload = decode_token(token)
        assert payload["sub"] == str(user.id)
        assert payload["email"] == "jwt@test.com"
        assert payload["role"] == "analyst"

    def test_invalid_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_token_contains_expiry(self):
        user = self._make_user()
        token = create_access_token(user)
        payload = decode_token(token)
        assert "exp" in payload
