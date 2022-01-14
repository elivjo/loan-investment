from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS

from ..models import Loan, CashFlow


class UserPermission(permissions.BasePermission):
    """All permissions for admin otherwise read-only"""

    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True
        return request.method in SAFE_METHODS
