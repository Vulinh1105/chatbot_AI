import { useAuthStore } from "../../stores/authStore";

function Header() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  return (
    <header className="app-header">
      <div className="header-title">
        <h1>Document Chatbot</h1>
      </div>

      <div className="header-user">
        <span>{user?.name || user?.email || "Người dùng"}</span>

        <button type="button" onClick={logout}>
          Đăng xuất
        </button>
      </div>
    </header>
  );
}

export default Header;