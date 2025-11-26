import { useStore } from '../store/useStore';
import { Permission } from '../types/rbac';

export function usePermissions() {
  const { user } = useStore();

  const hasPermission = (permission: Permission): boolean => {
    if (!user) return false;
    return user.permissions.includes(permission);
  };

  const hasAnyPermission = (permissions: Permission[]): boolean => {
    if (!user) return false;
    return permissions.some((perm) => user.permissions.includes(perm));
  };

  const hasAllPermissions = (permissions: Permission[]): boolean => {
    if (!user) return false;
    return permissions.every((perm) => user.permissions.includes(perm));
  };

  const isAdmin = (): boolean => {
    return user?.role === 'ADMIN';
  };

  const canAccessTrace = (): boolean => {
    return hasPermission('TRACE:READ');
  };

  const canCapture = (): boolean => {
    return hasPermission('TRACE:CAPTURE');
  };

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isAdmin,
    canAccessTrace,
    canCapture,
    permissions: user?.permissions || [],
    role: user?.role,
  };
}
