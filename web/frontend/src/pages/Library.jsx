import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Tile from "../components/Tile.jsx";
import Topbar from "../components/Topbar.jsx";

function mergeBooks(current, incoming) {
  const seen = new Set(incoming.map((book) => book.id));
  const next = [...incoming];
  for (const book of current) {
    if (String(book.id).startsWith("tmp-") && !seen.has(book.id)) {
      next.unshift(book);
    }
  }
  return next;
}

export default function Library({ showToast }) {
  const [books, setBooks] = useState([]);
  const [dragging, setDragging] = useState(false);
  const navigate = useNavigate();
  const depth = useRef(0);
  const fileRef = useRef(null);
  const uploadRef = useRef(null);

  const refresh = useCallback(async () => {
    const data = await api.library();
    setBooks((current) => mergeBooks(current, data.books || []));
  }, []);

  useEffect(() => {
    let source;
    let closed = false;
    refresh().catch((err) => showToast(err.message || "Could not load library"));

    function connect() {
      if (closed) {
        return;
      }
      source = new EventSource("/api/library/stream");
      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setBooks((current) => mergeBooks(current, data.books || []));
        } catch {
          /* ignore */
        }
      };
      source.onerror = () => {
        source.close();
        if (!closed) {
          window.setTimeout(connect, 2000);
        }
      };
    }
    connect();
    return () => {
      closed = true;
      source?.close();
    };
  }, [refresh, showToast]);

  useEffect(() => {
    function onEnter(event) {
      event.preventDefault();
      depth.current += 1;
      setDragging(true);
    }
    function onLeave(event) {
      event.preventDefault();
      depth.current = Math.max(0, depth.current - 1);
      if (!depth.current) {
        setDragging(false);
      }
    }
    function onOver(event) {
      event.preventDefault();
    }
    function onDrop(event) {
      event.preventDefault();
      depth.current = 0;
      setDragging(false);
      if (event.dataTransfer?.files) {
        uploadRef.current?.(event.dataTransfer.files);
      }
    }
    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("dragover", onOver);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("dragover", onOver);
      window.removeEventListener("drop", onDrop);
    };
  }, []);

  async function uploadFiles(fileList) {
    const files = [...fileList].filter((file) => file.name.toLowerCase().endsWith(".pdf"));
    if (!files.length) {
      showToast("Drop PDF files");
      return;
    }
    for (const file of files) {
      const tempId = `tmp-${crypto.randomUUID()}`;
      setBooks((current) => [
        {
          id: tempId,
          title: file.name.replace(/\.pdf$/i, ""),
          status: "uploading",
          progress: 3,
          has_cover: false,
        },
        ...current,
      ]);
      try {
        const book = await api.upload(file);
        setBooks((current) => [book, ...current.filter((item) => item.id !== tempId)]);
      } catch (err) {
        setBooks((current) => current.filter((item) => item.id !== tempId));
        showToast(err.message || "Upload failed");
      }
    }
  }
  uploadRef.current = uploadFiles;

  return (
    <>
      <Topbar
        extra={
          <label className="nav-item add-btn">
            Add PDFs
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              hidden
              onChange={(event) => {
                uploadFiles(event.target.files);
                event.target.value = "";
              }}
            />
          </label>
        }
      />
      <main className="page">
        <div className="page-head">
          <div>
            <h1 className="page-title">Library</h1>
            <p className="page-sub">
              Drop PDFs anywhere. They convert one at a time on the server — closing this tab does
              not stop a job.
            </p>
          </div>
        </div>
        {books.length === 0 ? (
          <div className="empty">
            <div className="diamond" />
            <strong>Your shelf is empty</strong>
            <p>Drop PDF files here, or use Add PDFs in the header</p>
          </div>
        ) : (
          <div className="grid">
            {books.map((book) => (
              <Tile
                key={book.id}
                book={book}
                onOpen={(item) => navigate(`/books/${item.id}`)}
                onCancel={async (item) => {
                  try {
                    await api.cancel(item.id);
                  } catch (err) {
                    showToast(err.message);
                  }
                }}
                onRetry={async (item) => {
                  try {
                    await api.retry(item.id);
                  } catch (err) {
                    showToast(err.message);
                  }
                }}
                onDelete={async (item) => {
                  if (!confirm(`Delete “${item.title}” and its processed files?`)) {
                    return;
                  }
                  try {
                    await api.remove(item.id);
                    setBooks((current) => current.filter((row) => row.id !== item.id));
                  } catch (err) {
                    showToast(err.message);
                  }
                }}
                onZip={(item) => {
                  window.location.href = `/api/books/${item.id}/zip`;
                }}
              />
            ))}
          </div>
        )}
      </main>
      <div className={`drop-veil${dragging ? " visible" : ""}`}>Drop PDFs to add to library</div>
    </>
  );
}
