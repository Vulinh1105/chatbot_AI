import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
import axios from "axios";
import { getCurrentUser, login as loginApi } from "../../services/authService";

function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");

    if (!username.trim() || !password) {
      setError("Vui lòng nhập đầy đủ email và mật khẩu.");
      return;
    }

    setLoading(true);

    try {
      const response = await loginApi({
        username: username.trim(),
        password,
      });

      localStorage.setItem("accessToken", response.access_token);

      const user = await getCurrentUser();

      login(user, response.access_token);

      navigate("/chat", { replace: true });
    } catch (error) {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail || "Email hoặc mật khẩu không đúng."
        : "Email hoặc mật khẩu không đúng.";

      setError(message);
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
            <label htmlFor="username">
              Email hoặc tên đăng nhập
            </label>

            <input
              id="username"
              name="username"
              type="text"
              placeholder="Nhập email hoặc tên đăng nhập"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              disabled={loading}
              required
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
