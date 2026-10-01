import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import SetupPage from "./pages/SetupPage";
import SessionLayout from "./pages/SessionLayout";
import SessionDetail from "./pages/SessionDetail";

function AuthGuard() {
  const { user, loading, setupRequired } = useAuth();
  if (loading) {
    return (
      <div
        role="status"
        className="flex h-screen items-center justify-center text-sm text-muted"
      >
        Opening…
      </div>
    );
  }
  if (setupRequired) {
    return <Navigate to="/setup" replace />;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route element={<AuthGuard />}>
          <Route path="/" element={<Navigate to="/sessions" replace />} />
          <Route path="/sessions" element={<SessionLayout />}>
            <Route index element={<SessionDetail />} />
            <Route path=":sessionId" element={<SessionDetail />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
