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
        <span className="whitespace-nowrap inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">
          <ShieldAlert className="w-3.5 h-3.5 text-purple-600 shrink-0" />
          <span>SYSTEM OWNER (ADMIN)</span>
        </span>
      );
    }

    switch (role) {
      case 'ADMIN':
        return (
          <span className="whitespace-nowrap inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-700 border border-purple-200">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
            <span>ADMIN</span>
          </span>
        );
      case 'IT_ASSET_MANAGER':
        return (
          <span className="whitespace-nowrap inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-700 border border-indigo-200">
            <UserCheck className="w-3.5 h-3.5 shrink-0" />
            <span>IT MANAGER</span>
          </span>
        );
      case 'MANAGER':
        return (
          <span className="whitespace-nowrap inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">
            <UserCheck className="w-3.5 h-3.5 shrink-0" />
            <span>MANAGER</span>
          </span>
        );
      default:
        return (
          <span className="whitespace-nowrap inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            <Users className="w-3.5 h-3.5 shrink-0" />
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
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
        <Navbar />

        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Top Header */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-purple-100 border border-purple-200 flex items-center justify-center text-purple-700">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  Quản lý Người dùng & Phân quyền
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Quản lý tài khoản, liên kết Keycloak SSO và phân quyền vai trò (Role Source of Truth: PostgreSQL)
                </p>
              </div>
            </div>

            <button
              onClick={loadUsers}
              disabled={loading}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
              <span>Làm mới</span>
            </button>
          </div>

          {/* Feedback Alert */}
          {feedback && (
            <div
              className={`p-4 rounded-xl border text-xs font-medium flex items-center space-x-3 shadow-sm ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
            >
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <div className="flex-1 font-semibold">{feedback.message}</div>
              <button
                onClick={() => setFeedback(null)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>
          )}

          {/* Stats Overview */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200/90 rounded-2xl p-4 flex items-center justify-between shadow-sm">
              <div>
                <div className="text-xs text-slate-500 font-medium">Tổng người dùng</div>
                <div className="text-2xl font-extrabold text-slate-900 mt-1">{users.length}</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600">
                <Users className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl p-4 flex items-center justify-between shadow-sm">
              <div>
                <div className="text-xs text-purple-700 font-semibold">System Owner (ADMIN)</div>
                <div className="text-2xl font-extrabold text-purple-800 mt-1">{adminCount}</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
                <ShieldCheck className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl p-4 flex items-center justify-between shadow-sm">
              <div>
                <div className="text-xs text-indigo-700 font-semibold">IT Asset Managers</div>
                <div className="text-2xl font-extrabold text-indigo-800 mt-1">{itManagerCount}</div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                <UserCheck className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl p-4 flex items-center justify-between shadow-sm">
              <div>
                <div className="text-xs text-emerald-700 font-semibold">Managers / Employees</div>
                <div className="text-2xl font-extrabold text-emerald-800 mt-1">
                  {managerCount + employeeCount}
                </div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                <Users className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Filter and Search Bar */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Tìm tên, email, phòng ban..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white transition-all"
              />
            </div>

            <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
              <span className="text-xs text-slate-500 font-medium">Lọc theo Role:</span>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 text-xs text-slate-800 rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500 font-medium"
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
            <div className="bg-white border border-slate-200/90 rounded-2xl p-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center space-y-3 shadow-sm">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
              <p>Đang tải danh sách người dùng...</p>
            </div>
          ) : error ? (
            <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center text-rose-800 text-xs shadow-sm">
              {error}
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="bg-white border border-slate-200/90 rounded-2xl p-12 text-center text-slate-500 text-xs shadow-sm">
              Không tìm thấy người dùng phù hợp với điều kiện tìm kiếm.
            </div>
          ) : (
            <div className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider text-[11px] font-bold border-b border-slate-200">
                    <tr className="whitespace-nowrap">
                      <th className="py-3.5 px-4 min-w-[200px]">Người dùng</th>
                      <th className="py-3.5 px-4 min-w-[150px]">Phòng ban</th>
                      <th className="py-3.5 px-4 min-w-[150px]">Vai trò hiện tại</th>
                      <th className="py-3.5 px-4 min-w-[140px]">Keycloak SSO</th>
                      <th className="py-3.5 px-4 min-w-[120px]">Ngày tạo</th>
                      <th className="py-3.5 px-4 text-right min-w-[200px]">Hành động Phân quyền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filteredUsers.map((u) => {
                      const isOwner = u.email === SYSTEM_OWNER_EMAIL;
                      const currentSelectedRole = pendingRoles[u.id] || u.role;
                      const hasChanged = currentSelectedRole !== u.role;
                      const isUpdating = updatingId === u.id;

                      return (
                        <tr
                          key={u.id}
                          className={`hover:bg-slate-50 transition-colors ${
                            isOwner ? 'bg-purple-50/40 hover:bg-purple-50/70' : ''
                          }`}
                        >
                          {/* User details */}
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-3">
                              <div
                                className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm border ${
                                  isOwner
                                    ? 'bg-purple-100 text-purple-700 border-purple-200'
                                    : 'bg-indigo-50 text-indigo-600 border-indigo-100'
                                }`}
                              >
                                {u.full_name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div className="font-extrabold text-slate-900 flex items-center space-x-2">
                                  <span>{u.full_name}</span>
                                  {isOwner && (
                                    <span className="text-[10px] bg-purple-100 text-purple-800 px-1.5 py-0.2 rounded font-mono font-bold">
                                      Owner
                                    </span>
                                  )}
                                </div>
                                <div className="text-[11px] text-slate-500">{u.email}</div>
                              </div>
                            </div>
                          </td>

                          {/* Department */}
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-1.5 text-slate-700 font-medium">
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
                                className="inline-flex items-center space-x-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-[11px] font-semibold"
                                title={`Keycloak UUID: ${u.keycloak_user_id}`}
                              >
                                <KeyRound className="w-3 h-3" />
                                <span>Đã kết nối</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full text-[11px] font-semibold">
                                <span>Tài khoản Nội bộ</span>
                              </span>
                            )}
                          </td>

                          {/* Created date */}
                          <td className="py-4 px-4">
                            <div className="flex items-center space-x-1 text-slate-500 text-[11px]">
                              <Calendar className="w-3.5 h-3.5" />
                              <span>
                                {new Date(u.created_at).toLocaleDateString('vi-VN')}
                              </span>
                            </div>
                          </td>

                          {/* Role Control Action */}
                          <td className="py-4 px-4 text-right">
                            {isOwner ? (
                              <div className="inline-flex items-center space-x-1 text-slate-500 text-[11px] bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl font-medium">
                                <Lock className="w-3.5 h-3.5 text-purple-600" />
                                <span className="text-purple-700 font-bold">Bảo vệ Chủ hệ thống</span>
                              </div>
                            ) : (
                              <div className="inline-flex items-center space-x-2 justify-end">
                                <select
                                  value={currentSelectedRole}
                                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                  disabled={isUpdating}
                                  className="bg-slate-50 border border-slate-200 text-xs text-slate-800 font-medium rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
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
                                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-500/20'
                                      : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
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

