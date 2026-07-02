from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
import bcrypt


class User(Model):
    id = fields.IntField(pk=True)
    login = fields.CharField(50, unique=True)
    full_name = fields.CharField(100)
    phone = fields.CharField(20, null=True)
    password_hash = fields.CharField(128)
    is_active = fields.BooleanField(default=True)
    is_superadmin = fields.BooleanField(default=False)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt()
        ).decode()

    def verify_password(self, password: str):
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8")
        )
    

GetUser = pydantic_model_creator(User, name='User', exclude=['password_hash'])
CreateUser = pydantic_model_creator(
    User, name='UserIn', exclude_readonly=True, exclude=('is_superadmin',)
)