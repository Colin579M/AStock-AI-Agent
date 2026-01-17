/**
 * 管理员受保护的路由组件
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAdminAuth } from '../../contexts/AdminAuthContext';

interface AdminProtectedRouteProps {
  children: React.ReactNode;
}

export const AdminProtectedRoute: React.FC<AdminProtectedRouteProps> = ({ children }) => {
  const { isAdminAuthenticated, isLoading } = useAdminAuth();

  if (isLoading) {
    return (
      <div className="loading-screen admin-loading">
        <div className="spinner"></div>
        <p>验证管理员身份...</p>
      </div>
    );
  }

  if (!isAdminAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  return <>{children}</>;
};
