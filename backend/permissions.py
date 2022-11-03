from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(request.user == obj.user)


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.type == 'buyer')
