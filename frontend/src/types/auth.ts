/** Auth domain types, inferred from Zod rather than declared twice. */

import type { z } from 'zod';

import type {
  authResponseSchema,
  authSessionSchema,
  loginFormSchema,
  registerFormSchema,
  userSchema,
} from '@/schemas/authSchema';

export type User = z.infer<typeof userSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;
export type AuthSession = z.infer<typeof authSessionSchema>;
export type LoginForm = z.infer<typeof loginFormSchema>;
export type RegisterForm = z.infer<typeof registerFormSchema>;

/** Kết quả một lần đăng nhập/đăng ký: token + user + hạn token (ms). */
export interface AuthResult {
  token: string;
  user: User;
  expiresAt: number | null;
}

/** State of the sign-in / sign-up flow. */
export type AuthStatus = 'anonymous' | 'authenticating' | 'authenticated';

/** Per-field errors, keyed by the form field name. */
export type FieldErrors = Partial<Record<string, string>>;
