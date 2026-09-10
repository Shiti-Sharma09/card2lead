// Where the browser reaches the API.
// - Production: empty string -> same origin (the backend serves the built app too).
// - Local dev: also empty -> the Vite proxy forwards /auth, /events, /me,
//   /assignees, /health to the backend (see vite.config.js).
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export const APP_NAME = 'CARD2LEAD'

// Client-side sharpness cutoff used on the camera screen (tuned separately
// from anything server-side).
export const BLUR_THRESHOLD = Number(import.meta.env.VITE_BLUR_THRESHOLD || 120)
