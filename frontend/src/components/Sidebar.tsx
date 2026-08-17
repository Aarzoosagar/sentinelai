import { NavLink } from "react-router-dom";
import clsx from "clsx";
import {
  LayoutDashboard,
  Cloud,
  ShieldAlert,
  ClipboardCheck,
  FileText,
  MessageSquare,
  History,
  Settings as SettingsIcon,
  ShieldCheck,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/aws-accounts", label: "AWS Accounts", icon: Cloud },
  { to: "/findings", label: "Findings", icon: ShieldAlert },
  { to: "/compliance", label: "Compliance", icon: ClipboardCheck },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/chat", label: "AI Security Chat", icon: MessageSquare },
  { to: "/audit-history", label: "Audit History", icon: History },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-60 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 px-4 py-5">
        <ShieldCheck className="h-6 w-6 text-accent-blue" />
        <span className="text-base font-semibold tracking-tight">SentinelAI</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
                isActive
                  ? "bg-accent-blue/10 text-accent-blue"
                  : "text-text-secondary hover:bg-white/5 hover:text-text-primary"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-4 text-xs text-text-secondary">Read-only • Never modifies AWS</div>
    </aside>
  );
}
