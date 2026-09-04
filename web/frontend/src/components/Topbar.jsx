import { NavLink } from "react-router-dom";

export default function Topbar({ extra }) {
  return (
    <header className="topbar">
      <NavLink className="brand" to="/">
        <img src="/brand/logo.png" alt="" />
        Markdrop
      </NavLink>
      <nav className="nav">
        <NavLink to="/" end className="nav-item">
          Library
        </NavLink>
        <NavLink to="/settings" className="nav-item">
          Settings
        </NavLink>
        {extra}
      </nav>
    </header>
  );
}
