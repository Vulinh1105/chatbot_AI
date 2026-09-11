import { NavLink, useMatch } from "react-router-dom";
import ConversationList from "../chat/ConversationList";

function Sidebar() {
  const isChat = useMatch("/chat");
  return (
    <aside className="app-sidebar">
      <div className="sidebar-logo">
        <span>DocBot</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/chat"
          aria-label="Chat"
          title="Chat"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "active" : ""}`
          }
        >
          💬
          <span>Chat</span>
        </NavLink>

        <NavLink
          to="/documents"
          aria-label="Tài liệu"
          title="Tài liệu"
          className={({ isActive }) =>
            `sidebar-link ${isActive ? "active" : ""}`
          }
        >
          📄
          <span>Tài liệu</span>
        </NavLink>
      </nav>
      {isChat && <div className="conversation-desktop"><ConversationList /></div>}
    </aside>
  );
}

export default Sidebar;
