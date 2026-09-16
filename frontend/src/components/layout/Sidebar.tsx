import { NavLink } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">D</div>

        <div className="sidebar-brand-text">
          <strong>DocBot</strong>
          <span>Knowledge Assistant</span>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Điều hướng chính">
        <NavLink
          to="/chat"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "active" : ""}`
          }
        >
          <span className="sidebar-link-icon" aria-hidden="true">
            💬
          </span>
          <span className="sidebar-link-text">Chat</span>
        </NavLink>

        <NavLink
          to="/documents"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "active" : ""}`
          }
        >
          <span className="sidebar-link-icon" aria-hidden="true">
            📄
          </span>
          <span className="sidebar-link-text">Tài liệu</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <span className="sidebar-footer-text">Document Chatbot</span>
      </div>
    </aside>
  );
}

export default Sidebar;