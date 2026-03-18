"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Map,
  Shield,
  Activity,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/providers", label: "Providers", icon: Search },
  { href: "/claims", label: "Claims", icon: FileText },
  { href: "/heatmap", label: "Risk Map", icon: Map },
  { href: "/fairness", label: "Fairness", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r bg-background flex flex-col">
      <div className="flex items-center gap-2 px-4 py-4 border-b">
        <Activity className="h-5 w-5 text-primary" />
        <span className="font-semibold text-sm">CMS Fraud Detection</span>
      </div>
      <nav className="flex-1 px-2 py-3 space-y-1">
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
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t text-xs text-muted-foreground">
        v0.1.0
      </div>
    </aside>
  );
}
