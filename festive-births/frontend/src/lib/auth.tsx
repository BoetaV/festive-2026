"use client"

import useSWR from "swr"
import { api, ApiError } from "./api"
import type { Role, User } from "./types"

export function useAuth() {
  const { data, error, isLoading, mutate } = useSWR<User | null>(
    "/api/auth/me",
    async (url: string) => {
      try {
        return await api<User>(url)
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null
        throw e
      }
    },
    { revalidateOnFocus: true, shouldRetryOnError: false },
  )
  return { user: data ?? null, isLoading, error, mutate }
}

export const can = {
  edit: (u: User | null) => !!u && u.role !== "province",
  manageUsers: (u: User | null) => !!u && u.role !== "user",
  security: (u: User | null) => !!u && u.role !== "user",
  exportUsers: (u: User | null) => u?.role === "superuser",
  /** Mirrors the API's can_manage_user: who may edit, reset or remove `target`. */
  manageUser: (actor: User | null, target: User) => {
    if (!actor) return false
    if (actor.role === "superuser") return true
    if (actor.role === "province") return target.role === "admin" || target.role === "user"
    return actor.role === "admin" && target.role === "user" && target.district === actor.district
  },
}

export function hasRole(u: User | null, ...roles: Role[]) {
  return !!u && roles.includes(u.role)
}
