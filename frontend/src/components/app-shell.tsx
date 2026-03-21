"use client";

import { useState } from "react";
import { NavSidebar } from "@/components/nav-sidebar";
import { ChatSidebar } from "@/components/chat-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <NavSidebar
        onChatToggle={() => setChatOpen((o) => !o)}
        chatOpen={chatOpen}
      />
      <main className="flex-1 overflow-auto relative z-0">{children}</main>
      {chatOpen && <ChatSidebar onClose={() => setChatOpen(false)} />}
    </div>
  );
}
