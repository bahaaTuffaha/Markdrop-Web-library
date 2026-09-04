import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import Topbar from "../components/Topbar.jsx";

export default function Reader({ showToast }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [title, setTitle] = useState("Book");
  const [html, setHtml] = useState("Loading…");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const book = await api.book(id);
        if (cancelled) {
          return;
        }
        setTitle(book.title);
        if (book.status !== "ready") {
          setHtml(`<p>This book is still ${book.status}.</p>`);
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
        const body = await response.text();
        if (!cancelled) {
          setHtml(body);
        }
      } catch (err) {
        if (!cancelled) {
          setHtml(err.message || "Could not open this book.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function onDelete() {
    if (!confirm(`Delete “${title}” and its processed files?`)) {
      return;
    }
    try {
      await api.remove(id);
      navigate("/");
    } catch (err) {
      showToast(err.message);
    }
  }

  return (
    <div className="reader-shell">
      <Topbar />
      <main className="page reader-wrap">
        <div className="reader-bar">
          <Link to="/" className="back-btn">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M10 3.5 5.5 8 10 12.5"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Library
          </Link>
          <h1 className="reader-title">{title}</h1>
          <div className="actions-row">
            <a className="btn secondary" href={`/api/books/${id}/zip`}>
              Download zip
            </a>
            <button className="btn danger" type="button" onClick={onDelete}>
              Delete
            </button>
          </div>
        </div>
        <article className="markdown" dangerouslySetInnerHTML={{ __html: html }} />
      </main>
    </div>
  );
}
