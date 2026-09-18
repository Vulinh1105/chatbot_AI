import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
import axios from "axios";
import {
  getCurrentUser,
  login as loginApi,
} from "../../services/authService";
import "../Auth/Auth.css";

function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setError("");

    if (!username.trim() || !password) {
      setError(
        "Vui lòng nhập đầy đủ email và mật khẩu."
      );
      return;
    }

    setLoading(true);

    try {
      const response = await loginApi({
        username: username.trim(),
        password,
      });

      localStorage.setItem(
        "accessToken",
        response.access_token
      );

      const user = await getCurrentUser();

      login(user, response.access_token);

      navigate("/chat", { replace: true });
    } catch (error) {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail ||
          "Email hoặc mật khẩu không đúng."
        : "Email hoặc mật khẩu không đúng.";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      className={`auth-page ${
        showPassword
          ? "password-focus-mode"
          : ""
      }`}
    >
      <div className="auth-background" />

      <section className="auth-card">
        <header className="auth-header">
          <div
            className="auth-logo"
            aria-hidden="true"
          >
            D
          </div>

          <h1>Đăng nhập</h1>

          <p>
            Đăng nhập vào hệ thống Document Chatbot
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="auth-form"
        >
          {/* USERNAME */}

          <div className="auth-form-group">
            <label htmlFor="username">
              Email hoặc tên đăng nhập
            </label>

            <div className="auth-input-wrapper">
              <span
                className="auth-input-icon"
                aria-hidden="true"
              >
                @
              </span>

              <input
                id="username"
                name="username"
                type="text"
                placeholder="Nhập email hoặc tên đăng nhập"
                value={username}
                onChange={(event) =>
                  setUsername(
                    event.target.value
                  )
                }
                autoComplete="username"
                disabled={loading}
                required
              />
            </div>
          </div>

          {/* PASSWORD */}

          <div className="auth-form-group password-group">
            <label htmlFor="password">
              Mật khẩu
            </label>

            <div className="auth-password-wrapper">
              <span
                className="auth-input-icon"
                aria-hidden="true"
              >
                🔒
              </span>

              <input
                id="password"
                name="password"
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                placeholder="Nhập mật khẩu"
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value
                  )
                }
                autoComplete="current-password"
                disabled={loading}
                required
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() =>
                  setShowPassword(
                    (previous) => !previous
                  )
                }
                disabled={loading}
                aria-label={
                  showPassword
                    ? "Ẩn mật khẩu"
                    : "Hiển thị mật khẩu"
                }
              >
                <span>
                  {showPassword
                    ? "◉"
                    : "◉"}
                </span>
              </button>
            </div>
          </div>

          {error && (
            <div
              className="auth-error"
              role="alert"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "Đang đăng nhập..."
              : "Đăng nhập →"}
          </button>
        </form>

        <div className="auth-footer">
          Chưa có tài khoản?{" "}
          <Link to="/register">
            Đăng ký
          </Link>
        </div>
      </section>
    </main>
  );
}

export default LoginPage;