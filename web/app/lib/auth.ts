/**
 * Authentication token management with migration support
 *
 * Migrates from old 'agentforge_token' to new 'framemind_token'
 * while maintaining backward compatibility.
 */

const OLD_TOKEN_KEY = "agentforge_token";
const NEW_TOKEN_KEY = "framemind_token";

/**
 * Get the authentication token, migrating from old key if necessary
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;

  // First try new token key
  const newToken = localStorage.getItem(NEW_TOKEN_KEY);
  if (newToken) return newToken;

  // Fall back to old token key and migrate
  const oldToken = localStorage.getItem(OLD_TOKEN_KEY);
  if (oldToken) {
    // Migrate to new key
    localStorage.setItem(NEW_TOKEN_KEY, oldToken);
    localStorage.removeItem(OLD_TOKEN_KEY);
    return oldToken;
  }

  return null;
}

/**
 * Set the authentication token (always uses new key)
 */
export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(NEW_TOKEN_KEY, token);
}

/**
 * Remove the authentication token from both keys
 */
export function removeAuthToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(NEW_TOKEN_KEY);
  localStorage.removeItem(OLD_TOKEN_KEY);
}
