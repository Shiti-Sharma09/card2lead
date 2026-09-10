// JWT storage. Kept in memory + localStorage so a reload stays signed in.
const KEY = 'c2l_token'

let current = null
try {
  current = localStorage.getItem(KEY) || null
} catch {
  /* private mode / storage disabled */
}

export function getToken() {
  return current
}

export function setToken(token) {
  current = token || null
  try {
    if (token) localStorage.setItem(KEY, token)
    else localStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
}
