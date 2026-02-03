import { OnboardingModal } from "@/components/OnboardingModal";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Auth is now handled by AppShell in root layout
  return (
    <>
      <OnboardingModal />
      {children}
    </>
  );
}
