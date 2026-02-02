export type UserRole = "free" | "premium" | "admin";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  profile: UserProfile | null;
}

// Role-based permissions
export const ROLE_PERMISSIONS = {
  free: {
    maxDailyPicks: 3,
    canAccessRag: false,
    canAccessHistory: false,
    canAccessAlerts: false,
    canAccessAdmin: false,
  },
  premium: {
    maxDailyPicks: Infinity,
    canAccessRag: true,
    canAccessHistory: true,
    canAccessAlerts: true,
    canAccessAdmin: false,
  },
  admin: {
    maxDailyPicks: Infinity,
    canAccessRag: true,
    canAccessHistory: true,
    canAccessAlerts: true,
    canAccessAdmin: true,
  },
} as const;

export function getRolePermissions(role: UserRole) {
  return ROLE_PERMISSIONS[role];
}

export function hasPermission(
  role: UserRole,
  permission: keyof (typeof ROLE_PERMISSIONS)["free"]
): boolean {
  return !!ROLE_PERMISSIONS[role][permission];
}
