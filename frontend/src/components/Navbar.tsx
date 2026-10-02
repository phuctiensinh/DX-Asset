'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
  ShieldCheck,
  LayoutDashboard,
  Boxes,
  UserCheck,
  AlertTriangle,
  LogOut,
  User as UserIcon,
  Bot,
  Wrench,
  BrainCircuit,
  Users,
  Building2,
} from 'lucide-react';

export function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'IT_ASSET_MANAGER':
        return 'bg-indigo-100 text-indigo-700 border-indigo-200';
      case 'MANAGER':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'EMPLOYEE':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const isManagementRole = user && ['ADMIN', 'IT_ASSET_MANAGER', 'MANAGER'].includes(user.role);

  const navLinks = [
    {
      href: '/dashboard',
      label: 'Tổng quan',
      icon: LayoutDashboard,
      active: pathname === '/dashboard',
    },
    ...(isManagementRole
      ? [
          {
            href: '/intelligence',
            label: 'Trí tuệ Tài sản',
            icon: BrainCircuit,
            active: pathname.startsWith('/intelligence'),
          },
        ]
      : []),
    ...(user?.role === 'ADMIN'
      ? [
          {
            href: '/users',
            label: 'Người dùng',
            icon: Users,
            active: pathname.startsWith('/users'),
          },
        ]
      : []),
    {
      href: '/departments',
      label: 'Phòng ban',
      icon: Building2,
      active: pathname.startsWith('/departments'),
    },
    {
      href: '/assets',
      label: 'Quản lý tài sản',
      icon: Boxes,
      active: pathname.startsWith('/assets'),
    },
    {
      href: '/assignments',
      label: 'Cấp phát tài sản',
      icon: UserCheck,
      active: pathname.startsWith('/assignments'),
    },
    {
      href: '/incidents',
      label: 'Quản lý sự cố',
      icon: AlertTriangle,
      active: pathname.startsWith('/incidents'),
    },
    {
      href: '/maintenance',
      label: 'Bảo trì thiết bị',
      icon: Wrench,
      active: pathname.startsWith('/maintenance'),
    },
    {
      href: '/assistant',
      label: 'Trợ lý AI',
      icon: Bot,
      active: pathname.startsWith('/assistant'),
    },
  ];

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/90 px-4 sm:px-8 py-3 flex items-center justify-between shadow-sm">
      <div className="flex items-center space-x-6">
        {/* Brand */}
        <Link href="/dashboard" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="font-extrabold text-lg text-slate-900 tracking-tight leading-tight">DX-Asset</div>
            <div className="text-[11px] font-medium text-indigo-600">Digital Asset Lifecycle</div>
          </div>
        </Link>

        {/* Navigation Tabs */}
        <nav className="hidden xl:flex items-center space-x-1 pl-4 border-l border-slate-200">
          {navLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                  link.active
                    ? 'bg-indigo-50 text-indigo-600 border border-indigo-100 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${link.active ? 'text-indigo-600' : 'text-slate-400'}`} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* Compact Nav for Medium screens */}
        <nav className="hidden md:flex xl:hidden items-center space-x-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`p-2 rounded-xl text-xs font-semibold ${
                  link.active
                    ? 'bg-indigo-50 text-indigo-600 border border-indigo-100'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
                title={link.label}
              >
                <Icon className="w-4 h-4" />
              </Link>
            );
          })}
        </nav>

        {/* User info pill */}
        <div className="hidden sm:flex items-center space-x-2.5 bg-slate-50 border border-slate-200/80 px-3.5 py-1.5 rounded-full text-xs shadow-inner">
          <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <span className="font-semibold text-slate-800">{user?.full_name}</span>
          <span
            className={`px-2 py-0.5 rounded-md border font-bold text-[10px] ${getRoleBadgeStyle(
              user?.role
            )}`}
          >
            {user?.role}
          </span>
        </div>

        <button
          onClick={logout}
          className="flex items-center space-x-1.5 px-3 py-2 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-600 text-xs font-semibold rounded-xl transition-all shadow-sm"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Đăng xuất</span>
        </button>
      </div>
    </header>
  );
}

