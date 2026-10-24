import type { ReactNode } from "react";
import { AuthGuard } from "@/components/auth-guard";
import { FocusSessionProvider } from "@/components/focus-session";
import { LanguageAccent } from "@/components/language-accent";
import { NativeLanguageGate } from "@/components/native-language-gate";
import { AppShell } from "@/components/shell";
import { TutorChatWidget } from "@/components/tutor-chat-widget";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <FocusSessionProvider>
      <LanguageAccent />
      <AuthGuard>
        <AppShell tutor={<TutorChatWidget />}>
          <NativeLanguageGate>{children}</NativeLanguageGate>
        </AppShell>
      </AuthGuard>
    </FocusSessionProvider>
  );
}
