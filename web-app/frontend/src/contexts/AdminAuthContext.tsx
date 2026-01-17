/**
 * 管理员认证上下文
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { adminApi } from '../api/adminClient';
import type { AdminLoginResponse } from '../api/adminClient';

interface AdminUser {
  user_id: string;
  name: string;
  role: 'admin';
}

interface AdminAuthContextType {
  admin: AdminUser | null;
  isAdminAuthenticated: boolean;
  isLoading: boolean;
  adminLogin: (accessCode: string) => Promise<AdminLoginResponse>;
  adminLogout: () => void;
}

const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);

export const AdminAuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [admin, setAdmin] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 初始化时检查本地存储的管理员认证状态
  useEffect(() => {
    const initAdminAuth = async () => {
      const token = localStorage.getItem('admin_token');
      const savedAdmin = localStorage.getItem('admin_user');

      if (token && savedAdmin) {
        try {
          // 验证 token 是否有效
          await adminApi.getCurrentAdmin();
          const parsedAdmin = JSON.parse(savedAdmin);
          if (parsedAdmin.role === 'admin') {
            setAdmin(parsedAdmin);
          } else {
            throw new Error('Not admin');
          }
        } catch {
          // token 无效，清除本地存储
          localStorage.removeItem('admin_token');
          localStorage.removeItem('admin_user');
        }
      }
      setIsLoading(false);
    };

    initAdminAuth();
  }, []);

  const adminLogin = async (accessCode: string): Promise<AdminLoginResponse> => {
    const response = await adminApi.login(accessCode);

    if (response.success && response.token && response.user) {
      // 验证是否是管理员
      if (response.user.role !== 'admin') {
        return {
          success: false,
          message: '该账号不是管理员',
        };
      }

      localStorage.setItem('admin_token', response.token);
      localStorage.setItem('admin_user', JSON.stringify(response.user));
      setAdmin(response.user as AdminUser);
    }

    return response;
  };

  const adminLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    setAdmin(null);
  };

  return (
    <AdminAuthContext.Provider
      value={{
        admin,
        isAdminAuthenticated: !!admin,
        isLoading,
        adminLogin,
        adminLogout,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
};

export const useAdminAuth = () => {
  const context = useContext(AdminAuthContext);
  if (context === undefined) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider');
  }
  return context;
};
