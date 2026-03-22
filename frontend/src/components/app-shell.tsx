"use client";

import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import { NavSidebar } from "@/components/nav-sidebar";
import { ChatSidebar } from "@/components/chat-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [chatOpen, setChatOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!sidebarOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      {!sidebarOpen && (
        <button
          type="button"
          aria-label="Open navigation"
          onClick={() => setSidebarOpen(true)}
          className="fixed top-4 left-4 z-50 lg:hidden neu-float rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <Menu className="h-5 w-5" />
        </button>
      )}

      {sidebarOpen && (
        <div
          role="presentation"
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <NavSidebar
        onChatToggle={() => setChatOpen((o) => !o)}
        chatOpen={chatOpen}
        sidebarOpen={sidebarOpen}
        onSidebarClose={() => setSidebarOpen(false)}
      />
      <main className="flex-1 overflow-auto relative z-0">{children}</main>
      {chatOpen && <ChatSidebar onClose={() => setChatOpen(false)} />}
    </div>
  );
}
