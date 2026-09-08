import { NavLink } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-logo">
        <span>DocBot</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/chat"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "active" : ""}`
          }
        >
          💬
          <span>Chat</span>
        </NavLink>

        <NavLink
          to="/documents"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "active" : ""}`
          }
        >
          📄
          <span>Tài liệu</span>
        </NavLink>
      </nav>
    </aside>
  );
}

export default Sidebar;