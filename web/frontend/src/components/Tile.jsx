import { memo } from "react";

const BUSY = new Set(["uploading", "queued", "processing", "cancelling"]);

function Tile({ book, onOpen, onCancel, onRetry, onDelete, onZip }) {
  const busy = BUSY.has(book.status);
  const ready = book.status === "ready";
  const percent = Math.max(0, Math.min(100, Number(book.progress) || 0));
  const cover = book.has_cover || book.cover_url;

  function handleClick(event) {
    if (event.target.closest("button")) {
      return;
    }
    if (ready) {
      onOpen(book);
    }
  }

  return (
    <article
      className={`tile ${book.status}`}
      onClick={handleClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" && ready) {
          onOpen(book);
        }
      }}
      role={ready ? "link" : "group"}
    >
      {cover ? (
        <>
          <img className="tile-cover" alt="" src={`/api/books/${book.id}/cover`} />
          {busy ? (
            <div className="tile-overlay">
              <div className="spinner small" />
              <div className="percent">{percent}%</div>
            </div>
          ) : null}
        </>
      ) : (
        <div className="placeholder">
          <div className="diamond">{busy ? <div className="spinner" /> : null}</div>
          <div className="percent">{busy ? `${percent}%` : book.status}</div>
        </div>
      )}
      {ready ? null : <div className={`badge ${book.status}`}>{book.status}</div>}
      {busy ? (
        <div className="tile-progress">
          <span style={{ width: `${percent}%` }} />
        </div>
      ) : null}
      <div className="actions">
        {busy && book.status !== "uploading" ? (
          <button type="button" onClick={() => onCancel(book)}>
            Cancel
          </button>
        ) : null}
        {ready ? (
          <>
            <button type="button" onClick={() => onZip(book)}>
              Download zip
            </button>
            <button type="button" className="danger" onClick={() => onDelete(book)}>
              Delete
            </button>
          </>
        ) : null}
        {book.status === "failed" || book.status === "cancelled" ? (
          <>
            <button type="button" onClick={() => onRetry(book)}>
              Retry
            </button>
            <button type="button" className="danger" onClick={() => onDelete(book)}>
              Delete
            </button>
          </>
        ) : null}
      </div>
      <div className="tile-title" title={book.title}>
        {book.title}
      </div>
    </article>
  );
}

function sameTile(prev, next) {
  const a = prev.book;
  const b = next.book;
  return (
    a.id === b.id &&
    a.status === b.status &&
    a.progress === b.progress &&
    a.has_cover === b.has_cover &&
    a.cover_url === b.cover_url &&
    a.title === b.title
  );
}

export default memo(Tile, sameTile);
