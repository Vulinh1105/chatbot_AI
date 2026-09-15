import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "../layouts/AppLayout";
import ChatPage from "../pages/Chat/ChatPage";
import DocumentManagementPage from "../pages/Documents/DocumentManagementPage";
import LoginPage from "../pages/Login/LoginPage";
import RegisterPage from "../pages/Register/RegisterPage";
import NotFoundPage from "../pages/NotFound/NotFoundPage";
import ProtectedRoute from "../components/common/ProtectedRoute";

function AppRoutes() {
  return (
    <Routes>
      {/* Trang đăng nhập */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Các trang yêu cầu đăng nhập */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/chat" element={<ChatPage />} />
          <Route
            path="/documents"
            element={<DocumentManagementPage />}
          />
        </Route>
      </Route>

      {/* Trang mặc định */}
      <Route path="/" element={<Navigate to="/chat" replace />} />

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default AppRoutes;