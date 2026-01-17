/**
 * 管理员登录页面
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import './AdminLoginPage.css';

export const AdminLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { adminLogin, isAdminAuthenticated } = useAdminAuth();
  const [accessCode, setAccessCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 如果已登录，跳转到管理后台
  React.useEffect(() => {
    if (isAdminAuthenticated) {
      navigate('/admin/users', { replace: true });
    }
  }, [isAdminAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessCode.trim()) {
      setError('请输入管理员访问码');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await adminLogin(accessCode);
      if (response.success) {
        navigate('/admin/users', { replace: true });
      } else {
        setError(response.message || '登录失败');
      }
    } catch (err) {
      setError('网络错误，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="admin-login-page">
      <div className="admin-login-container">
        <div className="admin-login-header">
          <div className="admin-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1>管理后台</h1>
          <p>请输入管理员访问码</p>
        </div>

        <form onSubmit={handleSubmit} className="admin-login-form">
          <div className="form-group">
            <input
              type="password"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
              placeholder="管理员访问码"
              disabled={isLoading}
              autoFocus
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={isLoading} className="login-btn">
            {isLoading ? (
              <>
                <span className="spinner-small"></span>
                验证中...
              </>
            ) : (
              '登录'
            )}
          </button>
        </form>

        <div className="admin-login-footer">
          <button onClick={() => navigate('/login')} className="back-link">
            返回普通登录
          </button>
        </div>
      </div>
    </div>
  );
};
