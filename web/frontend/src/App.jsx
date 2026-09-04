import { useCallback, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Library from "./pages/Library.jsx";
import Login from "./pages/Login.jsx";
import Reader from "./pages/Reader.jsx";
import Settings from "./pages/Settings.jsx";

export default function App() {
  const [toast, setToast] = useState("");
  const showToast = useCallback((message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2400);
  }, []);

  return (
    <>
      <Routes>
        <Route path="/" element={<Library showToast={showToast} />} />
        <Route path="/settings" element={<Settings showToast={showToast} />} />
        <Route path="/books/:id" element={<Reader showToast={showToast} />} />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {toast ? <div className="toast show">{toast}</div> : null}
    </>
  );
}
