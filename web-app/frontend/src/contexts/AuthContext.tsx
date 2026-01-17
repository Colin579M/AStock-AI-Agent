/**
 * 认证上下文
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/client';
import type { LoginResponse } from '../api/client';

interface User {
  user_id: string;
  name: string;
  expires_at: string | null;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isFirstLogin: boolean;
  login: (accessCode: string) => Promise<LoginResponse>;
  logout: () => void;
  setFirstLoginComplete: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFirstLogin, setIsFirstLogin] = useState(false);

  // 初始化时检查本地存储的认证状态
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      const savedUser = localStorage.getItem('user');

      if (token && savedUser) {
        try {
          // 验证 token 是否有效
          await authApi.getCurrentUser();
          setUser(JSON.parse(savedUser));
        } catch {
          // token 无效，清除本地存储
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (accessCode: string): Promise<LoginResponse> => {
    const response = await authApi.login(accessCode);

    if (response.success && response.token && response.user) {
      localStorage.setItem('token', response.token);
      localStorage.setItem('user', JSON.stringify(response.user));
      setUser(response.user);
      setIsFirstLogin(response.is_first_login || false);
    }

    return response;
  };

  const logout = () => {
    authApi.logout().catch(() => {});
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  const setFirstLoginComplete = () => {
    setIsFirstLogin(false);
    localStorage.setItem('first_login_complete', 'true');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        isFirstLogin,
        login,
        logout,
        setFirstLoginComplete,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
