'use client';

import React, { useEffect, useState } from 'react';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { useAuth } from '@/lib/auth-context';
import { fetchApi } from '@/lib/api';
import {
  Users,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  KeyRound,
  Search,
  RefreshCw,
  UserCheck,
  Building2,
  Calendar,
  Lock,
} from 'lucide-react';

interface DepartmentInfo {
  id: number;
  code: string;
  name: string;
}

interface UserItem {
  id: number;
  keycloak_user_id?: string | null;
  email: string;
  full_name: string;
  role: 'ADMIN' | 'IT_ASSET_MANAGER' | 'MANAGER' | 'EMPLOYEE';
  department_id?: number | null;
  department?: DepartmentInfo | null;
  is_active: boolean;
  created_at: string;
}

const SYSTEM_OWNER_EMAIL = '2424801030008@student.tdmu.edu.vn';

export default function UserManagementPage() {
  const { user: currentUser, loadCurrentUser } = useAuth();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [pendingRoles, setPendingRoles] = useState<Record<number, string>>({});
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi<UserItem[]>('/users');
      setUsers(data || []);
      const initialRoles: Record<number, string> = {};
      (data || []).forEach((u) => {
        initialRoles[u.id] = u.role;
      });
      setPendingRoles(initialRoles);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách người dùng. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleRoleChange = (userId: number, newRole: string) => {
    setPendingRoles((prev) => ({ ...prev, [userId]: newRole }));
  };

  const handleUpdateRole = async (targetUser: UserItem) => {
    const selectedRole = pendingRoles[targetUser.id];
    if (!selectedRole || selectedRole === targetUser.role) return;

    if (targetUser.email === SYSTEM_OWNER_EMAIL) {
      setFeedback({
        type: 'error',
        message: 'Không thể thay đổi role của System Owner.',
      });
      return;
    }

    if (selectedRole === 'ADMIN') {
      setFeedback({
        type: 'error',
        message: 'Không thể gán quyền ADMIN cho tài khoản khác. Chỉ System Owner giữ vai trò ADMIN.',
      });
      return;
    }

    setUpdatingId(targetUser.id);
    setFeedback(null);

    try {
      const updated = await fetchApi<UserItem>(`/users/${targetUser.id}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role: selectedRole }),
      });

      setUsers((prev) =>
        prev.map((u) => (u.id === updated.id ? { ...u, role: updated.role } : u))
      );
      setPendingRoles((prev) => ({ ...prev, [updated.id]: updated.role }));
      setFeedback({
        type: 'success',
        message: `Đã cập nhật vai trò của "${targetUser.full_name}" thành ${updated.role} thành công!`,
      });

      // Refresh current user if self updated
      if (currentUser?.id === targetUser.id) {
        await loadCurrentUser();
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Cập nhật vai trò thất bại.',
      });
      // Revert pending role selection
      setPendingRoles((prev) => ({ ...prev, [targetUser.id]: targetUser.role }));
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.department?.name && u.department.name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesRole = roleFilter === 'ALL' || u.role === roleFilter;

    return matchesSearch && matchesRole;
  });

  const getRoleBadge = (role: string, email: string) => {
    if (email === SYSTEM_OWNER_EMAIL) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
          <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />
          <span>SYSTEM OWNER (ADMIN)</span>
        </span>
      );
    }

    switch (role) {
      case 'ADMIN':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>ADMIN</span>
          </span>
        );
      case 'IT_ASSET_MANAGER':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
            <UserCheck className="w-3.5 h-3.5" />
            <span>IT MANAGER</span>
          </span>
        );
      case 'MANAGER':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <UserCheck className="w-3.5 h-3.5" />
            <span>MANAGER</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <Users className="w-3.5 h-3.5" />
            <span>EMPLOYEE</span>
          </span>
        );
    }
  };

  const adminCount = users.filter((u) => u.role === 'ADMIN').length;
  const itManagerCount = users.filter((u) => u.role === 'IT_ASSET_MANAGER').length;
  const managerCount = users.filter((u) => u.role === 'MANAGER').length;
  const employeeCount = users.filter((u) => u.role === 'EMPLOYEE').length;

  return (
    <ProtectedRoute allowedRoles={['ADMIN']}>
      <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
        <Navbar />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          {/* Top Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
            <div>
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Quản lý Người dùng & Phân quyền
                  </h1>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Quản lý tài khoản, liên kết Keycloak SSO và phân quyền vai trò (Role Source of Truth: PostgreSQL)
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={loadUsers}
              disabled={loading}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Làm mới</span>
            </button>
          </div>

          {/* Feedback Alert */}
          {feedback && (
            <div
              className={`p-4 rounded-xl border text-sm flex items-start space-x-3 shadow-md transition-all ${
                feedback.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-red-500/10 border-red-500/30 text-red-300'
              }`}
            >
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1 font-medium">{feedback.message}</div>
              <button
                onClick={() => setFeedback(null)}
                className="text-xs opacity-70 hover:opacity-100"
              >
                ✕
              </button>
            </div>
          )}

          {/* Stats Overview */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-400 font-medium">Tổng người dùng</div>
                <div className="text-2xl font-bold text-white mt-1">{users.length}</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
                <Users className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="text-xs text-purple-400 font-medium">System Owner (ADMIN)</div>
                <div className="text-2xl font-bold text-purple-300 mt-1">{adminCount}</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="text-xs text-indigo-400 font-medium">IT Asset Managers</div>
                <div className="text-2xl font-bold text-indigo-300 mt-1">{itManagerCount}</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <UserCheck className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="text-xs text-emerald-400 font-medium">Managers / Employees</div>
                <div className="text-2xl font-bold text-emerald-300 mt-1">
                  {managerCount + employeeCount}
                </div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Users className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Filter and Search Bar */}
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Tìm tên, email, phòng ban..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-500 transition-colors"
              />
            </div>

            <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
              <span className="text-xs text-slate-400">Lọc theo Role:</span>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-slate-900/80 border border-slate-700/80 text-xs text-white rounded-xl px-3 py-2 focus:outline-none focus:border-sky-500"
              >
                <option value="ALL">Tất cả vai trò</option>
                <option value="ADMIN">ADMIN (System Owner)</option>
                <option value="IT_ASSET_MANAGER">IT_ASSET_MANAGER</option>
                <option value="MANAGER">MANAGER</option>
                <option value="EMPLOYEE">EMPLOYEE</option>
              </select>
            </div>
          </div>

          {/* Main User Table */}
          {loading ? (
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin text-sky-400" />
              <p>Đang tải danh sách người dùng...</p>
            </div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center text-red-300 text-xs">
              {error}
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-12 text-center text-slate-400 text-xs">
              Không tìm thấy người dùng phù hợp với điều kiện tìm kiếm.
            </div>
          ) : (
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800/90 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-700/80">
                    <tr>
                      <th className="py-3.5 px-4 font-semibold">Người dùng</th>
                      <th className="py-3.5 px-4 font-semibold">Phòng ban</th>
                      <th className="py-3.5 px-4 font-semibold">Vai trò hiện tại</th>
                      <th className="py-3.5 px-4 font-semibold">Keycloak SSO</th>
                      <th className="py-3.5 px-4 font-semibold">Ngày tạo</th>
                      <th className="py-3.5 px-4 font-semibold text-right">Hành động Phân quyền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50 text-slate-300">
                    {filteredUsers.map((u) => {
                      const isOwner = u.email === SYSTEM_OWNER_EMAIL;
                      const currentSelectedRole = pendingRoles[u.id] || u.role;
                      const hasChanged = currentSelectedRole !== u.role;
                      const isUpdating = updatingId === u.id;

                      return (
                        <tr
                          key={u.id}
                          className={`hover:bg-slate-800/50 transition-colors ${
                            isOwner ? 'bg-purple-500/5 hover:bg-purple-500/10' : ''
                          }`}
                        >
                          {/* User details */}
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-3">
                              <div
                                className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm border ${
                                  isOwner
                                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                                    : 'bg-slate-700/80 text-sky-400 border-slate-600'
                                }`}
                              >
                                {u.full_name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div className="font-semibold text-white flex items-center space-x-2">
                                  <span>{u.full_name}</span>
                                  {isOwner && (
                                    <span className="text-[10px] bg-purple-500/30 text-purple-200 px-1.5 py-0.2 rounded font-mono">
                                      Owner
                                    </span>
                                  )}
                                </div>
                                <div className="text-[11px] text-slate-400">{u.email}</div>
                              </div>
                            </div>
                          </td>

                          {/* Department */}
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-1.5 text-slate-300">
                              <Building2 className="w-3.5 h-3.5 text-slate-400" />
                              <span>{u.department ? u.department.name : 'Chưa phân bổ'}</span>
                            </div>
                          </td>

                          {/* Role Badge */}
                          <td className="py-4 px-4">{getRoleBadge(u.role, u.email)}</td>

                          {/* Keycloak SSO status */}
                          <td className="py-4 px-4">
                            {u.keycloak_user_id ? (
                              <span
                                className="inline-flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full text-[11px]"
                                title={`Keycloak UUID: ${u.keycloak_user_id}`}
                              >
                                <KeyRound className="w-3 h-3" />
                                <span>Đã kết nối</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 text-slate-400 bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full text-[11px]">
                                <span>Tài khoản Nội bộ</span>
                              </span>
                            )}
                          </td>

                          {/* Created date */}
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-1 text-slate-400 text-[11px]">
                              <Calendar className="w-3.5 h-3.5" />
                              <span>
                                {new Date(u.created_at).toLocaleDateString('vi-VN')}
                              </span>
                            </div>
                          </td>

                          {/* Role Control Action */}
                          <td className="py-4 px-4 text-right">
                            {isOwner ? (
                              <div className="inline-flex items-center space-x-1 text-slate-400 text-[11px] bg-slate-800/80 border border-slate-700/80 px-3 py-1.5 rounded-xl">
                                <Lock className="w-3.5 h-3.5 text-purple-400" />
                                <span className="text-purple-300 font-medium">Bảo vệ Chủ hệ thống</span>
                              </div>
                            ) : (
                              <div className="inline-flex items-center space-x-2 justify-end">
                                <select
                                  value={currentSelectedRole}
                                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                  disabled={isUpdating}
                                  className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-sky-500 disabled:opacity-50"
                                >
                                  <option value="EMPLOYEE">EMPLOYEE</option>
                                  <option value="MANAGER">MANAGER</option>
                                  <option value="IT_ASSET_MANAGER">IT_ASSET_MANAGER</option>
                                </select>

                                <button
                                  onClick={() => handleUpdateRole(u)}
                                  disabled={!hasChanged || isUpdating}
                                  className={`px-3 py-1.5 text-xs font-semibold rounded-xl transition-all flex items-center space-x-1 ${
                                    hasChanged && !isUpdating
                                      ? 'bg-sky-500 hover:bg-sky-600 text-white shadow-md shadow-sky-500/20'
                                      : 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
                                  }`}
                                >
                                  {isUpdating ? (
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <span>Cập nhật</span>
                                  )}
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
