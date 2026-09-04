const api = {
  async request(path, options = {}) {
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
      } catch (_err) {
        /* ignore */
      }
      throw new Error(detail);
    }
    const type = response.headers.get("content-type") || "";
    if (type.includes("application/json")) {
      return response.json();
    }
    return response;
  },
  health() {
    return this.request("/api/health");
  },
  library() {
    return this.request("/api/library");
  },
  book(id) {
    return this.request(`/api/books/${id}`);
  },
  async upload(file) {
    const body = new FormData();
    body.append("file", file);
    return this.request("/api/library", { method: "POST", body });
  },
  cancel(id) {
    return this.request(`/api/books/${id}/cancel`, { method: "POST" });
  },
  retry(id) {
    return this.request(`/api/books/${id}/retry`, { method: "POST" });
  },
  remove(id) {
    return this.request(`/api/books/${id}`, { method: "DELETE" });
  },
  markdown(id) {
    return fetch(`/api/books/${id}/markdown`).then(async (response) => {
      if (response.status === 401) {
        window.location.href = "/login";
      }
      if (!response.ok) {
        throw new Error("Markdown is not ready");
      }
      return response.text();
    });
  },
  settings() {
    return this.request("/api/settings");
  },
  saveSettings(payload) {
    return this.request("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  login(password) {
    return this.request("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
  },
};

function toast(message) {
  const el = document.getElementById("toast");
  if (!el) {
    return;
  }
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}

function navHighlight() {
  const path = window.location.pathname;
  document.querySelectorAll(".nav a").forEach((link) => {
    const href = link.getAttribute("href");
    if (href === "/" && path === "/") {
      link.classList.add("active");
    } else if (href !== "/" && path.startsWith(href)) {
      link.classList.add("active");
    }
  });
}

document.addEventListener("DOMContentLoaded", navHighlight);
