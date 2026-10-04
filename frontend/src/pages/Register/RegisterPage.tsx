import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../../services/authService";
import axios from "axios";
import "../Auth/Auth.css";

function RegisterPage() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (
      !username.trim() ||
      !email.trim() ||
      !password ||
      !confirmPassword
    ) {
      setError("Vui lòng nhập đầy đủ thông tin.");
      return;
    }

    if (password.length < 8) {
      setError(
        "Mật khẩu phải có ít nhất 8 ký tự."
      );
      return;
    }

    if (password !== confirmPassword) {
      setError(
        "Mật khẩu xác nhận không khớp."
      );
      return;
    }

    setLoading(true);

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
      });

      setSuccess(
        "Đăng ký thành công! Đang chuyển đến trang đăng nhập..."
      );

      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 800);
    } catch (error) {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail ||
          "Đăng ký thất bại. Vui lòng thử lại."
        : "Đăng ký thất bại. Vui lòng thử lại.";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-card">
        <header className="auth-header">
          <div className="auth-logo" aria-hidden="true">
            D
          </div>

          <h1>Đăng ký</h1>

          <p>
            Tạo tài khoản Document Chatbot
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="auth-form"
        >
          <div className="auth-form-group">
            <label htmlFor="username">
              Tên đăng nhập
            </label>

            <input
              id="username"
              name="username"
              type="text"
              placeholder="Nhập tên đăng nhập"
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
              autoComplete="username"
              disabled={loading}
              required
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="email">
              Email
            </label>

            <input
              id="email"
              name="email"
              type="email"
              placeholder="Nhập email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              autoComplete="email"
              disabled={loading}
              required
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="password">
              Mật khẩu
            </label>

            <input
              id="password"
              name="password"
              type="password"
              placeholder="Nhập mật khẩu"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              autoComplete="new-password"
              disabled={loading}
              required
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="confirmPassword">
              Xác nhận mật khẩu
            </label>

            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              placeholder="Nhập lại mật khẩu"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(event.target.value)
              }
              autoComplete="new-password"
              disabled={loading}
              required
            />
          </div>

          {error && (
            <div
              className="auth-error"
              role="alert"
            >
              {error}
            </div>
          )}

          {success && (
            <div
              className="auth-success"
              role="status"
            >
              {success}
            </div>
          )}

          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "Đang đăng ký..."
              : "Đăng ký"}
          </button>
        </form>

        <div className="auth-footer">
          Đã có tài khoản?{" "}
          <Link to="/login">
            Đăng nhập
          </Link>
        </div>
      </section>
    </main>
  );
}

export default RegisterPage;