"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { NavSidebar } from "@/components/nav-sidebar";
import { ChatSidebar } from "@/components/chat-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [chatOpen, setChatOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <button
        type="button"
        aria-label="Open navigation"
        onClick={() => setSidebarOpen(true)}
        className="fixed top-4 left-4 z-50 lg:hidden neu-float rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <Menu className="h-5 w-5" />
      </button>

      {sidebarOpen && (
        <div
          role="button"
          tabIndex={0}
          aria-label="Close navigation"
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => e.key === "Escape" && setSidebarOpen(false)}
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
