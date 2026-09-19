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
} from 'lucide-react';

export function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'IT_ASSET_MANAGER':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      case 'MANAGER':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'EMPLOYEE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const navLinks = [
    {
      href: '/dashboard',
      label: 'Tổng quan',
      icon: LayoutDashboard,
      active: pathname === '/dashboard',
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
    <header className="sticky top-0 z-30 bg-slate-800/90 backdrop-blur border-b border-slate-700/80 px-4 sm:px-8 py-3.5 flex items-center justify-between shadow-md">
      <div className="flex items-center space-x-6">
        {/* Brand */}
        <Link href="/dashboard" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="font-bold text-lg text-white leading-tight">DX-Asset</div>
            <div className="text-xs text-slate-400">Digital Asset Lifecycle</div>
          </div>
        </Link>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-700/60">
          {navLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                  link.active
                    ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center space-x-4">
        {/* Mobile Nav Link shortcut */}
        <div className="flex md:hidden items-center space-x-2">
          {navLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`p-2 rounded-lg text-xs font-semibold ${
                  link.active
                    ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-white'
                }`}
                title={link.label}
              >
                <Icon className="w-5 h-5" />
              </Link>
            );
          })}
        </div>

        {/* User info pill */}
        <div className="hidden sm:flex items-center space-x-3 bg-slate-900/60 border border-slate-700/60 px-3.5 py-1.5 rounded-full text-xs">
          <UserIcon className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-slate-200">{user?.full_name}</span>
          <span
            className={`px-2 py-0.5 rounded-md border font-medium text-[10px] ${getRoleBadgeStyle(
              user?.role
            )}`}
          >
            {user?.role}
          </span>
        </div>

        <button
          onClick={logout}
          className="flex items-center space-x-2 px-3.5 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-semibold rounded-xl transition-all"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Đăng xuất</span>
        </button>
      </div>
    </header>
  );
}
