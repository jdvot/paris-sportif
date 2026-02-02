export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Auth is now handled by AppShell in root layout
  return <>{children}</>;
}
