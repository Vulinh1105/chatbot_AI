import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "../layouts/AppLayout";
import ChatPage from "../pages/Chat/ChatPage";
import DocumentManagementPage from "../pages/Documents/DocumentManagementPage";
import NotFoundPage from "../pages/NotFound/NotFoundPage";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />

      <Route element={<AppLayout />}>
        <Route path="/chat" element={<ChatPage />} />
        <Route
          path="/documents"
          element={<DocumentManagementPage />}
        />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default AppRoutes;