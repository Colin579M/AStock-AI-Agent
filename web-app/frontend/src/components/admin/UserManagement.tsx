/**
 * 用户管理页面
 */
import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/adminClient';
import type { UserInfo, CreateUserRequest } from '../../api/adminClient';
import './UserManagement.css';

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCodeModal, setShowCodeModal] = useState(false);
  const [generatedCode, setGeneratedCode] = useState('');
  const [createdUserId, setCreatedUserId] = useState('');

  // 加载用户列表
  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.listUsers();
      setUsers(data);
      setError('');
    } catch (err) {
      setError('加载用户列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // 创建用户
  const handleCreateUser = async (data: CreateUserRequest) => {
    try {
      const response = await adminApi.createUser(data);
      if (response.success) {
        setGeneratedCode(response.access_code);
        setCreatedUserId(response.user_id);
        setShowCreateModal(false);
        setShowCodeModal(true);
        loadUsers();
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError('创建用户失败');
    }
  };

  // 删除用户
  const handleDeleteUser = async (userId: string) => {
    if (!confirm(`确定要删除用户 "${userId}" 吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await adminApi.deleteUser(userId);
      loadUsers();
    } catch (err) {
      setError('删除用户失败');
    }
  };

  // 重置访问码
  const handleResetCode = async (userId: string) => {
    if (!confirm(`确定要重置用户 "${userId}" 的访问码吗？旧访问码将失效。`)) {
      return;
    }

    try {
      const response = await adminApi.resetUserCode(userId);
      setGeneratedCode(response.access_code);
      setCreatedUserId(userId);
      setShowCodeModal(true);
    } catch (err) {
      setError('重置访问码失败');
    }
  };

  // 切换用户状态
  const handleToggleActive = async (userId: string, currentActive: boolean) => {
    try {
      await adminApi.updateUser(userId, { is_active: !currentActive });
      loadUsers();
    } catch (err) {
      setError('更新用户状态失败');
    }
  };

  // 复制到剪贴板
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // 格式化日期
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  return (
    <div className="user-management">
      <div className="admin-page-header">
        <h1>用户管理</h1>
        <p>管理系统用户和访问权限</p>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>×</button>
        </div>
      )}

      <div className="admin-card">
        <div className="admin-card-header">
          <h2 className="admin-card-title">用户列表</h2>
          <button className="admin-btn admin-btn-primary" onClick={() => setShowCreateModal(true)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            添加用户
          </button>
        </div>

        {isLoading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>加载中...</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>用户ID</th>
                  <th>名称</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th>登录次数</th>
                  <th>最后登录</th>
                  <th>过期时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.user_id}>
                    <td>
                      <span className="user-id">{user.user_id}</span>
                    </td>
                    <td>{user.name}</td>
                    <td>
                      <span className={`status-badge ${user.role === 'admin' ? 'status-badge-info' : 'status-badge-success'}`}>
                        {user.role === 'admin' ? '管理员' : '普通用户'}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${user.is_active ? 'status-badge-success' : 'status-badge-error'}`}>
                        {user.is_active ? '启用' : '禁用'}
                      </span>
                    </td>
                    <td>{user.login_count}</td>
                    <td>{formatDate(user.last_login)}</td>
                    <td>{user.expires_at ? formatDate(user.expires_at) : '永不过期'}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className="admin-btn admin-btn-secondary admin-btn-icon"
                          onClick={() => handleToggleActive(user.user_id, user.is_active)}
                          title={user.is_active ? '禁用用户' : '启用用户'}
                        >
                          {user.is_active ? (
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                              <line x1="1" y1="1" x2="23" y2="23" />
                            </svg>
                          ) : (
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                              <circle cx="12" cy="12" r="3" />
                            </svg>
                          )}
                        </button>
                        <button
                          className="admin-btn admin-btn-secondary admin-btn-icon"
                          onClick={() => handleResetCode(user.user_id)}
                          title="重置访问码"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        </button>
                        <button
                          className="admin-btn admin-btn-danger admin-btn-icon"
                          onClick={() => handleDeleteUser(user.user_id)}
                          title="删除用户"
                          disabled={user.role === 'admin' && users.filter(u => u.role === 'admin').length <= 1}
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 创建用户模态框 */}
      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateUser}
        />
      )}

      {/* 显示访问码模态框 */}
      {showCodeModal && (
        <div className="admin-modal-overlay" onClick={() => setShowCodeModal(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3 className="admin-modal-title">访问码已生成</h3>
              <button className="admin-modal-close" onClick={() => setShowCodeModal(false)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="admin-modal-body">
              <p className="code-notice">
                请妥善保管以下访问码，它将只显示一次：
              </p>
              <div className="code-display">
                <code>{generatedCode}</code>
                <button
                  className="copy-btn"
                  onClick={() => copyToClipboard(generatedCode)}
                  title="复制"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                </button>
              </div>
              <p className="code-user">用户：{createdUserId}</p>
            </div>
            <div className="admin-modal-footer">
              <button className="admin-btn admin-btn-primary" onClick={() => setShowCodeModal(false)}>
                我已保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// 创建用户模态框组件
interface CreateUserModalProps {
  onClose: () => void;
  onSubmit: (data: CreateUserRequest) => void;
}

const CreateUserModal: React.FC<CreateUserModalProps> = ({ onClose, onSubmit }) => {
  const [userId, setUserId] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [expiresAt, setExpiresAt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim() || !name.trim()) return;

    setIsSubmitting(true);
    await onSubmit({
      user_id: userId.trim(),
      name: name.trim(),
      role,
      expires_at: expiresAt || undefined,
    });
    setIsSubmitting(false);
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3 className="admin-modal-title">添加用户</h3>
          <button className="admin-modal-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="admin-modal-body">
            <div className="admin-form-group">
              <label className="admin-form-label">用户ID *</label>
              <input
                type="text"
                className="admin-input"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="唯一标识，如 user001"
                required
              />
              <p className="admin-form-hint">用于系统识别，创建后不可修改</p>
            </div>

            <div className="admin-form-group">
              <label className="admin-form-label">名称 *</label>
              <input
                type="text"
                className="admin-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="显示名称"
                required
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-form-label">角色</label>
              <select
                className="admin-select"
                value={role}
                onChange={(e) => setRole(e.target.value as 'user' | 'admin')}
              >
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </select>
            </div>

            <div className="admin-form-group">
              <label className="admin-form-label">过期时间</label>
              <input
                type="datetime-local"
                className="admin-input"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
              <p className="admin-form-hint">留空表示永不过期</p>
            </div>
          </div>

          <div className="admin-modal-footer">
            <button type="button" className="admin-btn admin-btn-secondary" onClick={onClose}>
              取消
            </button>
            <button
              type="submit"
              className="admin-btn admin-btn-primary"
              disabled={isSubmitting || !userId.trim() || !name.trim()}
            >
              {isSubmitting ? '创建中...' : '创建用户'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
