// RBAC Types based on FSD-Trace specification

export type Role = 'ADMIN' | 'ANALYST' | 'USER';

export type Permission =
  | 'TRACE:READ'
  | 'TRACE:CAPTURE'
  | 'REPORT:READ'
  | 'DATA:UPLOAD'
  | 'CHAT:USE';

export interface RoleDefinition {
  name: Role;
  description: string;
  permissions: Permission[];
}

export const ROLE_DEFINITIONS: Record<Role, RoleDefinition> = {
  ADMIN: {
    name: 'ADMIN',
    description: '시스템 관리자',
    permissions: [
      'TRACE:READ',
      'TRACE:CAPTURE',
      'REPORT:READ',
      'DATA:UPLOAD',
      'CHAT:USE',
    ],
  },
  ANALYST: {
    name: 'ANALYST',
    description: '분석 담당자',
    permissions: ['REPORT:READ', 'DATA:UPLOAD', 'CHAT:USE'],
  },
  USER: {
    name: 'USER',
    description: '일반 사용자',
    permissions: ['REPORT:READ', 'CHAT:USE'],
  },
};

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  permissions: Permission[];
  createdAt: string;
}

export interface AuditLogEntry {
  id: string;
  user: string;
  action: string;
  target?: string;
  result: 'success' | 'failure';
  timestamp: string;
  details?: Record<string, any>;
}
