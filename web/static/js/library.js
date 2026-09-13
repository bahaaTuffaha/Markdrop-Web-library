const books = new Map();

function tempBookId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `tmp-${crypto.randomUUID()}`;
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
    return `tmp-${hex}`;
  }
  return `tmp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function isBusy(status) {
  return ["uploading", "queued", "processing", "cancelling"].includes(status);
}

function mergeBooks(list) {
  const seen = new Set();
  for (const book of list) {
    seen.add(book.id);
    books.set(book.id, book);
  }
  for (const id of [...books.keys()]) {
    if (!seen.has(id) && !String(id).startsWith("tmp-")) {
      books.delete(id);
    }
  }
}

function tileHtml(book) {
  const busy = isBusy(book.status);
  const ready = book.status === "ready";
  const percent = Math.max(0, Math.min(100, Number(book.progress) || 0));
  const cover = book.has_cover || book.cover_url;
  let body;
  if (cover) {
    const overlay = busy
      ? `<div class="tile-overlay"><div class="spinner small"></div><div class="percent">${percent}%</div></div>`
      : "";
    body = `<img class="tile-cover" alt="" src="/api/books/${book.id}/cover">${overlay}`;
  } else {
    body = `<div class="placeholder">
      <div class="diamond">${busy ? '<div class="spinner"></div>' : ""}</div>
      <div class="percent">${busy ? `${percent}%` : book.status}</div>
    </div>`;
  }

  let actions = "";
  if (busy && book.status !== "uploading") {
    actions = `<div class="actions"><button data-act="cancel">Cancel</button></div>`;
  } else if (ready) {
    actions = `<div class="actions">
      <button data-act="zip">Download zip</button>
      <button class="danger" data-act="delete">Delete</button>
    </div>`;
  } else if (book.status === "failed" || book.status === "cancelled") {
    actions = `<div class="actions">
      <button data-act="retry">Retry</button>
      <button class="danger" data-act="delete">Delete</button>
    </div>`;
  }

  const badge = ready
    ? ""
    : `<div class="badge ${book.status}">${book.status}</div>`;
  const title = `<div class="tile-title" title="${escapeHtml(book.title)}">${escapeHtml(book.title)}</div>`;
  return `<article class="tile ${book.status}" data-id="${book.id}">
    ${body}${badge}${actions}${title}
  </article>`;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/"/g, "&quot;");
}

function render() {
  const grid = document.getElementById("grid");
  const empty = document.getElementById("empty");
  const items = [...books.values()];
  if (!items.length) {
    grid.innerHTML = "";
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  grid.innerHTML = items.map(tileHtml).join("");
}

async function refresh() {
  const data = await api.library();
  mergeBooks(data.books || []);
  render();
}

function connectStream() {
  const source = new EventSource("/api/library/stream");
  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      mergeBooks(data.books || []);
      render();
    } catch (_err) {
      /* ignore */
    }
  };
  source.onerror = () => {
    source.close();
    setTimeout(connectStream, 2000);
  };
}

async function uploadFiles(fileList) {
  const files = [...fileList].filter((file) => file.name.toLowerCase().endsWith(".pdf"));
  if (!files.length) {
    toast("Drop PDF files");
    return;
  }
  for (const file of files) {
    const tempId = tempBookId();
    books.set(tempId, {
      id: tempId,
      title: file.name.replace(/\.pdf$/i, ""),
      status: "uploading",
      progress: 3,
      has_cover: false,
    });
    render();
    try {
      const book = await api.upload(file);
      books.delete(tempId);
      books.set(book.id, book);
      render();
    } catch (err) {
      books.delete(tempId);
      render();
      toast(err.message || "Upload failed");
    }
  }
}

function setupDrop() {
  let depth = 0;
  window.addEventListener("dragenter", (event) => {
    event.preventDefault();
    depth += 1;
    document.body.classList.add("dragging");
  });
  window.addEventListener("dragleave", (event) => {
    event.preventDefault();
    depth = Math.max(0, depth - 1);
    if (!depth) {
      document.body.classList.remove("dragging");
    }
  });
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => {
    event.preventDefault();
    depth = 0;
    document.body.classList.remove("dragging");
    if (event.dataTransfer && event.dataTransfer.files) {
      uploadFiles(event.dataTransfer.files);
    }
  });
  document.getElementById("file-input").addEventListener("change", (event) => {
    uploadFiles(event.target.files);
    event.target.value = "";
  });
}

document.getElementById("grid").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-act]");
  const tile = event.target.closest(".tile");
  if (!tile) {
    return;
  }
  const id = tile.dataset.id;
  if (String(id).startsWith("tmp-")) {
    return;
  }
  const book = books.get(id);
  if (button) {
    event.preventDefault();
    event.stopPropagation();
    const act = button.dataset.act;
    try {
      if (act === "cancel") {
        await api.cancel(id);
      } else if (act === "delete") {
        if (!confirm(`Delete “${book.title}” and its processed files?`)) {
          return;
        }
        await api.remove(id);
        books.delete(id);
      } else if (act === "retry") {
        await api.retry(id);
      } else if (act === "zip") {
        window.location.href = `/api/books/${id}/zip`;
      }
      await refresh();
    } catch (err) {
      toast(err.message || "Action failed");
    }
    return;
  }
  if (book && book.status === "ready") {
    window.location.href = `/books/${id}`;
  }
});

setupDrop();
refresh()
  .then(connectStream)
  .catch((err) => toast(err.message || "Could not load library"));
