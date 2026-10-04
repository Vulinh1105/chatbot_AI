import { useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
import "./Header.css";

function Header() {
  const navigate = useNavigate();
  const location = useLocation();

  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const getPageInfo = () => {
    switch (location.pathname) {
      case "/documents":
        return {
          title: "Tài liệu",
          description: "Quản lý tài liệu và nguồn tri thức",
        };

      case "/chat":
      default:
        return {
          title: "Chat",
          description: "Tra cứu và hỏi đáp với tài liệu",
        };
    }
  };

  const pageInfo = getPageInfo();

  const displayName =
    user?.username || user?.email || "Người dùng";

  const avatarLetter = displayName
    .charAt(0)
    .toUpperCase();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="app-header">
      <div className="header-title">
        <h1>{pageInfo.title}</h1>
        <p>{pageInfo.description}</p>
      </div>

      <div className="header-user">
        <div className="header-user-info">
          <div
            className="header-avatar"
            aria-hidden="true"
          >
            {avatarLetter}
          </div>

          <div className="header-user-text">
            <span className="header-user-name">
              {displayName}
            </span>

            <span className="header-user-role">
              Người dùng
            </span>
          </div>
        </div>

        <button
          type="button"
          className="header-logout"
          onClick={handleLogout}
        >
          Đăng xuất
        </button>
      </div>
    </header>
  );
}

export default Header;