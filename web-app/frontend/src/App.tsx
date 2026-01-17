/**
 * TradingAgents Web App - 主入口
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AdminAuthProvider } from './contexts/AdminAuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { AdminProtectedRoute } from './components/common/AdminProtectedRoute';
import { LoginPage } from './components/auth/LoginPage';
import { GuidePage } from './components/onboarding/GuidePage';
import { HomePage } from './components/home/HomePage';
import { ChatPage } from './components/chat/ChatPage';
import { AnalysisPage } from './components/analysis/AnalysisPage';
import { HistoryPage } from './components/history/HistoryPage';
import { TrendRadarPage } from './components/trendradar/TrendRadarPage';
// Admin components
import { AdminLoginPage } from './components/admin/AdminLoginPage';
import { AdminLayout } from './components/admin/AdminLayout';
import { UserManagement } from './components/admin/UserManagement';
import { SystemMonitor } from './components/admin/SystemMonitor';
import { ContentManagement } from './components/admin/ContentManagement';
import { AdminLogs } from './components/admin/AdminLogs';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <AdminAuthProvider>
        <BrowserRouter>
          <Routes>
            {/* 公开路由 */}
            <Route path="/login" element={<LoginPage />} />

            {/* 受保护路由 */}
            <Route
              path="/guide"
              element={
                <ProtectedRoute>
                  <GuidePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/home"
              element={
                <ProtectedRoute>
                  <HomePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <ChatPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analysis"
              element={
                <ProtectedRoute>
                  <AnalysisPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analysis/:taskId"
              element={
                <ProtectedRoute>
                  <AnalysisPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analysis/result/:taskId"
              element={
                <ProtectedRoute>
                  <AnalysisPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/history"
              element={
                <ProtectedRoute>
                  <HistoryPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/trendradar"
              element={
                <ProtectedRoute>
                  <TrendRadarPage />
                </ProtectedRoute>
              }
            />

            {/* 管理后台路由 */}
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route
              path="/admin/users"
              element={
                <AdminProtectedRoute>
                  <AdminLayout>
                    <UserManagement />
                  </AdminLayout>
                </AdminProtectedRoute>
              }
            />
            <Route
              path="/admin/system"
              element={
                <AdminProtectedRoute>
                  <AdminLayout>
                    <SystemMonitor />
                  </AdminLayout>
                </AdminProtectedRoute>
              }
            />
            <Route
              path="/admin/content"
              element={
                <AdminProtectedRoute>
                  <AdminLayout>
                    <ContentManagement />
                  </AdminLayout>
                </AdminProtectedRoute>
              }
            />
            <Route
              path="/admin/logs"
              element={
                <AdminProtectedRoute>
                  <AdminLayout>
                    <AdminLogs />
                  </AdminLayout>
                </AdminProtectedRoute>
              }
            />
            <Route path="/admin" element={<Navigate to="/admin/users" replace />} />

            {/* 默认重定向 */}
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="*" element={<Navigate to="/home" replace />} />
          </Routes>
        </BrowserRouter>
      </AdminAuthProvider>
    </AuthProvider>
  );
}

export default App;
