import React, { Suspense } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  PlayCircle,
  Users,
  FileText,
  BriefcaseBusiness,
  Map as MapIcon,
  ShieldCheck,
  Database,
  Menu,
  X,
  CheckCircle2,
  LogOut,
} from "lucide-react";
import { cn } from "../lib/utils";
import { useAuth } from "../contexts/AuthContext";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Live Monitor", href: "/live", icon: Activity },
  { name: "Simulate", href: "/simulate", icon: PlayCircle },
  { name: "Providers", href: "/providers", icon: Users },
  { name: "Claims", href: "/claims", icon: FileText },
  { name: "Investigations", href: "/investigations", icon: BriefcaseBusiness },
  { name: "Risk Map", href: "/risk-map", icon: MapIcon },
  { name: "Fairness", href: "/fairness", icon: ShieldCheck },
  { name: "Analytics", href: "/analytics", icon: Database },
  { name: "Validation", href: "/validation", icon: CheckCircle2 },
];

export function Layout() {
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  const initials = user
    ? (user.full_name ?? user.username).slice(0, 2).toUpperCase()
    : "??";

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Mobile-only header */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 sticky top-0 z-50 shadow-sm md:hidden">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded flex items-center justify-center text-white font-bold text-lg">
            A
          </div>
          <span className="font-semibold text-lg tracking-tight text-slate-800">
            Argus
          </span>
        </div>
        <button
          className="p-2 text-slate-500"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={isMobileMenuOpen}
          aria-controls="sidebar-nav"
        >
          {isMobileMenuOpen ? (
            <X className="w-6 h-6" />
          ) : (
            <Menu className="w-6 h-6" />
          )}
        </button>
      </header>

      {/* Mobile backdrop */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-sm md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar — full height on desktop, slide-in on mobile */}
      <aside
        id="sidebar-nav"
        role="navigation"
        className={cn(
          "fixed inset-y-14 md:inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200 flex flex-col transform transition-transform duration-200 ease-in-out md:translate-x-0",
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Logo — desktop only */}
        <div className="shrink-0 h-14 hidden md:flex items-center gap-2.5 px-5 border-b border-slate-200">
          <div className="w-8 h-8 bg-indigo-600 rounded flex items-center justify-center text-white font-bold text-lg">
            A
          </div>
          <span className="font-semibold text-lg tracking-tight text-slate-800">
            Argus
          </span>
        </div>

        {/* Nav links */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                  isActive
                    ? "bg-indigo-50 text-indigo-700 shadow-sm"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                )
              }
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={cn(
                      "w-5 h-5 transition-colors",
                      isActive
                        ? "text-indigo-700"
                        : "group-hover:text-indigo-600",
                    )}
                  />
                  {item.name}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer — user profile + logout */}
        <div className="shrink-0 p-4 border-t border-slate-100">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-bold text-xs">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">
                  {user.full_name ?? user.username}
                </p>
                <p className="text-xs text-slate-400 capitalize">{user.role}</p>
              </div>
              <button
                onClick={logout}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : null}
        </div>
      </aside>

      {/* Main Content */}
      <main className="min-h-screen md:ml-64 overflow-y-auto bg-slate-50/50 p-6 md:p-8">
        <div className="max-w-7xl mx-auto">
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
