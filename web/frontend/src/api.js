export async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (response.status === 401 && !path.startsWith("/api/login")) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    return response.json();
  }
  return response;
}

export const api = {
  health: () => request("/api/health"),
  library: () => request("/api/library"),
  book: (id) => request(`/api/books/${id}`),
  upload(file) {
    const body = new FormData();
    body.append("file", file);
    return request("/api/library", { method: "POST", body });
  },
  cancel: (id) => request(`/api/books/${id}/cancel`, { method: "POST" }),
  retry: (id) => request(`/api/books/${id}/retry`, { method: "POST" }),
  remove: (id) => request(`/api/books/${id}`, { method: "DELETE" }),
  settings: () => request("/api/settings"),
  saveSettings: (payload) =>
    request("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  login: (password) =>
    request("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    }),
};
