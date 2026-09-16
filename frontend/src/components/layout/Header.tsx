import { useAuthStore } from "../../stores/authStore";

function Header() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const displayName = user?.username || user?.email || "Người dùng";

  return (
    <header className="app-header">
      <div className="header-title">
        <h1>Document Chatbot</h1>
        <p>Tra cứu và khai thác tri thức từ tài liệu</p>
      </div>

      <div className="header-user">
        <div className="header-user-info">
          <div className="header-avatar" aria-hidden="true">
            {displayName.charAt(0).toUpperCase()}
          </div>

          <div className="header-user-text">
            <span className="header-user-name">{displayName}</span>
            <span className="header-user-role">Người dùng</span>
          </div>
        </div>

        <button
          type="button"
          className="header-logout"
          onClick={logout}
        >
          Đăng xuất
        </button>
      </div>
    </header>
  );
}

export default Header;