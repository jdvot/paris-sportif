import { OnboardingModal } from "@/components/OnboardingModal";
import { FavoriteTeamModal } from "@/components/FavoriteTeamModal";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Auth is now handled by AppShell in root layout
  return (
    <>
      <OnboardingModal />
      <FavoriteTeamModal />
      {children}
    </>
  );
}
