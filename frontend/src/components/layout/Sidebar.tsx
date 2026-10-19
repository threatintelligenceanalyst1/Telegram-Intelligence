import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Settings, Key, Search } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
  { path: '/search', label: 'Global Search', icon: Search },
  { path: '/api-keys', label: 'Customer API Keys', icon: Key },
  { path: '/settings', label: 'Settings & Telethon', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-60 bg-darkCard border-r border-darkBorder flex flex-col justify-between shrink-0">
      <div className="py-4">
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
                      ? 'bg-blue-600/10 text-blue-600 font-bold border-l-2 border-blue-500 shadow-sm'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
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
      <div className="p-3.5 m-4 rounded-xl bg-darkBg border border-darkBorder flex items-center justify-between">
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
};
