import type { ReactNode } from "react";
import { AuthGuard } from "@/components/auth-guard";
import { Header, MobileNav, Sidebar } from "@/components/shell";
import { TutorChatWidget } from "@/components/tutor-chat-widget";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <Sidebar />
      <div className="min-h-screen lg:pl-64">
        <Header />
        <main className="mx-auto w-full max-w-6xl px-5 py-7 pb-28 md:px-8 md:py-10 lg:pb-10">{children}</main>
      </div>
      <MobileNav />
      <TutorChatWidget />
    </AuthGuard>
  );
}
