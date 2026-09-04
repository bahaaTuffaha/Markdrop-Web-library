import { useState } from "react";
import { api } from "../api.js";

export default function Login() {
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    const password = event.currentTarget.password.value;
    try {
      await api.login(password);
      window.location.href = "/";
    } catch {
      setError("Invalid password");
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <a className="brand" href="/" style={{ marginBottom: 16 }}>
          <img src="/brand/logo.png" alt="" />
          Markdrop
        </a>
        <label>
          Password
          <input type="password" name="password" required autoFocus />
        </label>
        <button className="btn" type="submit">
          Sign in
        </button>
        {error ? <p className="hint">{error}</p> : null}
      </form>
    </div>
  );
}
