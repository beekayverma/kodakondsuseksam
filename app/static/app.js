// kodakondsuseksam - shared client helpers.
// Keep this module tiny; per-page logic lives inline in the templates.

// --- Service worker registration -------------------------------------------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/static/sw.js", { scope: "/" })
      .catch(() => { /* offline-only nicety, never block the page */ });
  });
}

// --- Theme toggle (persists in localStorage) -------------------------------
const THEME_KEY = "kodakond.theme";
function applyTheme(theme) {
  if (theme === "light" || theme === "dark") {
    document.documentElement.setAttribute("data-theme", theme);
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
}
try {
  applyTheme(localStorage.getItem(THEME_KEY));
} catch (e) { /* private mode; ignore */ }

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    let next;
    if (current === "dark") next = "light";
    else if (current === "light") next = null; // back to system
    else next = "dark";
    applyTheme(next);
    try {
      if (next) localStorage.setItem(THEME_KEY, next);
      else localStorage.removeItem(THEME_KEY);
    } catch (e) { /* ignore */ }
  });
});

// --- Fetch helper ----------------------------------------------------------
export async function fetchJSON(url, init = {}) {
  const res = await fetch(url, {
    credentials: "same-origin",
    ...init,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${txt.slice(0, 200)}`);
  }
  return res.json();
}

// --- Timer formatting ------------------------------------------------------
export function formatMMSS(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

// --- Tiny event helper used by both pages ---------------------------------
export function on(el, type, fn, opts) {
  el.addEventListener(type, fn, opts);
  return () => el.removeEventListener(type, fn, opts);
}
