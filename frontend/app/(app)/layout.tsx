import type { ReactNode } from "react";
import { AuthGuard } from "@/components/auth-guard";
import { NativeLanguageGate } from "@/components/native-language-gate";
import { AppShell } from "@/components/shell";
import { TutorChatWidget } from "@/components/tutor-chat-widget";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppShell tutor={<TutorChatWidget />}>
        <NativeLanguageGate>{children}</NativeLanguageGate>
      </AppShell>
    </AuthGuard>
  );
}
