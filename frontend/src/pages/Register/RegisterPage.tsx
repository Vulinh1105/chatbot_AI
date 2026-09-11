import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

interface RegisteredUser {
  id: string;
  name: string;
  email: string;
  password: string;
}

function RegisterPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!name.trim() || !email.trim() || !password || !confirmPassword) {
      setError("Vui lòng nhập đầy đủ thông tin.");
      return;
    }

    if (password.length < 6) {
      setError("Mật khẩu phải có ít nhất 6 ký tự.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    setLoading(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 700));

      const registeredUsers: RegisteredUser[] = JSON.parse(
        localStorage.getItem("registeredUsers") || "[]"
      );

      const existingUser = registeredUsers.find(
        (user) => user.email.toLowerCase() === email.trim().toLowerCase()
      );

      if (existingUser) {
        setError("Email này đã được đăng ký.");
        return;
      }

      const newUser: RegisteredUser = {
        id: crypto.randomUUID(),
        name: name.trim(),
        email: email.trim(),
        password,
      };

      localStorage.setItem(
        "registeredUsers",
        JSON.stringify([...registeredUsers, newUser])
      );

      setSuccess(
        "Đăng ký thành công! Đang chuyển đến trang đăng nhập..."
      );

      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 800);
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

          <h1>Đăng ký</h1>

          <p>Tạo tài khoản Document Chatbot</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="name">Họ và tên</label>

            <input
              id="name"
              type="text"
              placeholder="Nhập họ và tên"
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={loading}
            />
          </div>

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

          <div className="form-group">
            <label htmlFor="confirmPassword">
              Xác nhận mật khẩu
            </label>

            <input
              id="confirmPassword"
              type="password"
              placeholder="Nhập lại mật khẩu"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(event.target.value)
              }
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          {success && (
            <div className="register-success">
              {success}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "Đang đăng ký..." : "Đăng ký"}
          </button>
        </form>

        <div className="register-login-link">
          Đã có tài khoản?{" "}
          <Link to="/login">Đăng nhập</Link>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;