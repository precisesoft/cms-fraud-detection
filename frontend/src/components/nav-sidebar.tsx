"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Search,
  Map,
  Shield,
  Activity,
  FileText,
  FlaskConical,
  MessageSquare,
  ClipboardList,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/investigate", label: "Inbox", icon: ClipboardList, badge: true },
  { href: "/simulate", label: "Simulate", icon: FlaskConical },
  { href: "/providers", label: "Providers", icon: Search },
  { href: "/claims", label: "Claims", icon: FileText },
  { href: "/heatmap", label: "Risk Map", icon: Map },
  { href: "/fairness", label: "Fairness", icon: Shield },
];

interface NavSidebarProps {
  onChatToggle: () => void;
  chatOpen: boolean;
}

export function NavSidebar({ onChatToggle, chatOpen }: NavSidebarProps) {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/cases/pending?limit=100`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: unknown) => {
        if (!cancelled && Array.isArray(data)) {
          setPendingCount(data.length);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <aside className="w-56 shrink-0 flex flex-col neu-card border-r border-border/50 relative z-10">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-border/50">
        <div className="flex h-8 w-8 items-center justify-center rounded-full neu-float">
          <Activity className="h-4 w-4 text-accent" />
        </div>
        <div>
          <span className="font-bold text-sm tracking-tight">ARGUS</span>
          <span className="label-stamped block text-[9px] leading-none mt-0.5">
            FRAUD DETECTION
          </span>
        </div>
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border/50">
        <div className="led-green" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          System Online
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-3 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-all duration-200",
                isActive
                  ? "neu-pressed text-accent font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:neu-subtle",
              )}
            >
              <item.icon className={cn("h-4 w-4", isActive && "text-accent")} />
              <span className="flex-1">{item.label}</span>
              {item.badge && pendingCount !== null && pendingCount > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
                  {pendingCount > 99 ? "99+" : pendingCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Chat toggle */}
      <div className="px-3 py-2 border-t border-border/50">
        <button
          type="button"
          onClick={onChatToggle}
          className={cn(
            "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm w-full transition-all duration-200",
            chatOpen
              ? "neu-pressed text-accent font-semibold"
              : "text-muted-foreground hover:text-foreground hover:neu-subtle",
          )}
        >
          <MessageSquare className={cn("h-4 w-4", chatOpen && "text-accent")} />
          Ask AI
        </button>
      </div>

      {/* Version */}
      <div className="px-4 py-2 border-t border-border/50">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          v0.1.0
        </span>
      </div>
    </aside>
  );
}
