import { NavLink } from "react-router-dom";
import ConversationList from "../chat/ConversationList";
import "./Sidebar.css";

function Sidebar() {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon" aria-hidden="true">
          D
        </div>

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

          <span className="sidebar-link-text">
            Chat
          </span>
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

          <span className="sidebar-link-text">
            Tài liệu
          </span>
        </NavLink>
      </nav>

      <div className="sidebar-conversations">
        <ConversationList />
      </div>

      <div className="sidebar-footer">
        <span>Document Chatbot</span>
      </div>
    </aside>
  );
}

export default Sidebar;