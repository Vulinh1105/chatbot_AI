import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";

function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");

    // Kiểm tra bỏ trống
    if (!email || !password) {
      setError("Vui lòng nhập đầy đủ email và mật khẩu.");
      return;
    }

    setLoading(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 700));

      const registeredUsers = JSON.parse(
        localStorage.getItem("registeredUsers") || "[]"
      );

      const registeredUser = registeredUsers.find(
        (user: { email: string; password: string }) =>
          user.email.toLowerCase() === email.trim().toLowerCase() &&
          user.password === password
      );

      const isDemoAccount =
        email.trim().toLowerCase() === "demo@docbot.local" &&
        password === "123456";

      if (!registeredUser && !isDemoAccount) {
        setError("Email hoặc mật khẩu không đúng.");
        return;
      }

      const user = registeredUser
        ? {
            id: registeredUser.id,
            email: registeredUser.email,
            name: registeredUser.name,
          }
        : {
            id: "demo-user",
            email: "demo@docbot.local",
            name: "Demo User",
          };

      login(user, "mock-access-token");

      navigate("/chat", { replace: true });
    } catch {
      setError("Đã xảy ra lỗi. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">DocBot</div>

          <h1>Đăng nhập</h1>

          <p>Đăng nhập vào hệ thống Document Chatbot</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>

            <input
              id="email"
              type="email"
              placeholder="Nhập email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Mật khẩu</label>

            <input
              id="password"
              type="password"
              placeholder="Nhập mật khẩu"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>

        <div className="register-login-link">
          Chưa có tài khoản?{" "}
          <Link to="/register">Đăng ký</Link>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
