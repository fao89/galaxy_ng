"""
Filesystem-only auth models without pulpcore dependencies.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Filesystem-based User model without pulpcore dependencies."""
    
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        pass


class Group(models.Model):
    """Filesystem-based Group model without pulpcore dependencies."""
    
    name = models.CharField(max_length=150, unique=True)
    
    class Meta:
        pass
    
    def __str__(self):
        return self.name