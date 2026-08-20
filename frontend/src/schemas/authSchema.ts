/**
 * Auth schemas.
 *
 * Session model: **JWT bearer** (see docs/API_CONTRACT.md). The backend issues an
 * access token on login; the frontend stores it and sends it back in the
 * `Authorization: Bearer <token>` header.
 */

import { z } from 'zod';

import { AUTH } from '@/utils/constants';

export const userSchema = z.object({
  id: z.string(),
  email: z.email(),
  display_name: z.string(),
  /** Avatar from Google; empty for email/password accounts. */
  avatar_url: z.string().nullish(),
  /** 'password' | 'google', so Settings can show how the account signs in. */
  provider: z.string().nullish(),
  created_at: z.string().nullish(),
});

/** Response of POST /auth/login and POST /auth/register — token + user. */
export const authResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default('bearer'),
  expires_in: z.number().int().nullish(),
  user: userSchema,
});

/** Response of GET /auth/me — a flat user object (not wrapped). */
export const meResponseSchema = userSchema;

/** Session persisted to localStorage so a page reload stays logged in. */
export const authSessionSchema = z.object({
  token: z.string(),
  user: userSchema,
  /** Token expiry, in milliseconds. Null if the token does not expire. */
  expires_at: z.number().nullish(),
});

// --- user input, validated in the form itself ---------------------------

export const loginFormSchema = z.object({
  email: z.email('Email không hợp lệ.'),
  password: z.string().min(1, 'Chưa nhập mật khẩu.'),
});

export const registerFormSchema = z
  .object({
    display_name: z
      .string()
      .trim()
      .min(1, 'Chưa nhập tên hiển thị.')
      .max(AUTH.maxDisplayNameLength, `Tên hiển thị tối đa ${AUTH.maxDisplayNameLength} ký tự.`),
    email: z.email('Email không hợp lệ.'),
    password: z
      .string()
      .min(AUTH.minPasswordLength, `Mật khẩu tối thiểu ${AUTH.minPasswordLength} ký tự.`)
      .max(AUTH.maxPasswordLength, `Mật khẩu tối đa ${AUTH.maxPasswordLength} ký tự.`),
    confirm_password: z.string(),
  })
  .refine((value) => value.password === value.confirm_password, {
    message: 'Hai lần nhập mật khẩu không khớp.',
    path: ['confirm_password'],
  });
