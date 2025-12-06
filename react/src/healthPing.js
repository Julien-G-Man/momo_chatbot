export async function pingHealth(apiBase) {
  if (!apiBase) return;
  try {
    await fetch(`${apiBase.replace(/\/$/, "")}/health`, { method: "GET", cache: "no-store" });
  } catch (e) {
    // Fail silently, we just want to wake the server
    console.warn("Backend health ping failed:", e);
  }
}
