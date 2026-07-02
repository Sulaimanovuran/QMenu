"""Refresh-токены для auth flow (/auth/refresh, /auth/logout)."""
from tortoise import fields
from tortoise.models import Model


class RefreshToken(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="refresh_tokens", on_delete=fields.CASCADE)
    token_hash = fields.CharField(64, unique=True)
    revoked = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField()
