"""DRF izin sınıfları — servis masası RBAC."""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .helpdesk import ROLE_ADMIN, ROLE_SUPPORT, is_support_staff, can_access_ticket


class IsSupportStaff(BasePermission):
    def has_permission(self, request, view):
        return is_support_staff(request.user)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.groups.filter(name=ROLE_ADMIN).exists()


class TicketObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_access_ticket(request.user, obj)


class TicketCommentPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if is_support_staff(request.user):
            return True
        return obj.author_id == request.user.id


class NotificationOwnerPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
