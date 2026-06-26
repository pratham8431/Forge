"use client"

import { auth } from "./firebase"

/** Get the current user's Firebase ID token (auto-refreshed by Firebase SDK). */
export async function getToken(): Promise<string | null> {
  try {
    return (await auth.currentUser?.getIdToken()) ?? null
  } catch {
    return null
  }
}
