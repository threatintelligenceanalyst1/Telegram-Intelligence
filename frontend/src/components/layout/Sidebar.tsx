import React, { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Settings, Key, Search, Shield, X, Pin, PinOff } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  isPinned: boolean;
  onTogglePin: () => void;
}

const navItems = [
  { path: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
  { path: '/search', label: 'Global Search', icon: Search },
  { path: '/api-keys', label: 'Customer API Keys', icon: Key },
  { path: '/settings', label: 'Settings & Telethon', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  isPinned,
  onTogglePin,
}) => {
  // Close hamburger drawer on Escape key
  useEffect(() => {
    if (!isOpen || isPinned) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isPinned, onClose]);

  // If pinned on desktop, render as standard docked sidebar
  if (isPinned) {
    return (
      <aside className="w-64 bg-darkCard border-r border-darkBorder flex flex-col justify-between shrink-0 h-[calc(100vh-3.5rem)] transition-all">
        <div className="py-3">
          <div className="px-4 pb-3 mb-2 border-b border-darkBorder flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Navigation
            </span>
            <button
              onClick={onTogglePin}
              className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold text-blue-600 hover:bg-blue-50 transition-colors"
              title="Unpin sidebar (switch to hamburger menu)"
            >
              <PinOff className="w-3 h-3" />
              <span>Unpin</span>
            </button>
          </div>

          <nav className="space-y-1 px-3">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* LLM Engine status indicator */}
        <div className="p-3 m-3 rounded-xl bg-darkBg border border-darkBorder flex items-center justify-between">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            LLM Engine
          </span>
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-600">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            Ready
          </div>
        </div>
      </aside>
    );
  }

  // If not open and not pinned, don't render anything
  if (!isOpen) {
    return null;
  }

  // Render as slide-out Hamburger Drawer overlay with backdrop
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Floating Hamburger Drawer */}
      <aside
        className="fixed top-0 bottom-0 left-0 z-50 w-72 bg-white border-r border-darkBorder shadow-2xl flex flex-col justify-between"
        role="dialog"
        aria-label="Navigation Menu"
      >
        <div>
          {/* Drawer Header */}
          <div className="h-14 px-4 border-b border-darkBorder flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                <Shield className="w-4 h-4" />
              </div>
              <div>
                <h2 className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                  Menu
                </h2>
                <span className="text-[10px] text-slate-400 font-medium">Darknet Intelligence</span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={onTogglePin}
                className="flex items-center gap-1 px-2 py-1 text-[11px] font-bold text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="Pin sidebar to page"
              >
                <Pin className="w-3.5 h-3.5" />
                <span>Pin</span>
              </button>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                title="Close menu"
                aria-label="Close menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 p-3">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-3 rounded-xl text-xs font-bold transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-semibold">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Drawer Footer */}
        <div className="p-3.5 m-3 rounded-xl bg-slate-50 border border-darkBorder flex items-center justify-between">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            LLM Engine
          </span>
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-600">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            Ready
          </div>
        </div>
      </aside>
    </>
  );
};
