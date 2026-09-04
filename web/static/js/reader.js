function bookIdFromPath() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  return parts[1] || "";
}

async function load() {
  const id = bookIdFromPath();
  const titleEl = document.getElementById("title");
  const content = document.getElementById("content");
  try {
    const book = await api.book(id);
    titleEl.textContent = book.title;
    document.getElementById("download").href = `/api/books/${id}/zip`;
    document.getElementById("delete").addEventListener("click", async () => {
      if (!confirm(`Delete “${book.title}” and its processed files?`)) {
        return;
      }
      await api.remove(id);
      window.location.href = "/";
    });
    if (book.status !== "ready") {
      content.innerHTML = `<p>This book is still ${book.status}.</p>`;
      return;
    }
    const response = await fetch(`/api/books/${id}/rendered`);
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      throw new Error("Markdown is not ready");
    }
    content.innerHTML = await response.text();
  } catch (err) {
    content.textContent = err.message || "Could not open this book.";
  }
}

load();
