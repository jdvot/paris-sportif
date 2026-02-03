"use client";

import { WifiOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function OfflinePage() {
  const handleRetry = () => {
    window.location.reload();
  };

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-6 rounded-full bg-slate-800 p-6">
        <WifiOff className="h-12 w-12 text-slate-400" />
      </div>

      <h1 className="mb-2 text-2xl font-bold text-white">
        Vous etes hors ligne
      </h1>

      <p className="mb-6 max-w-md text-slate-400">
        Impossible de se connecter au serveur. Verifiez votre connexion internet
        et reessayez.
      </p>

      <Button onClick={handleRetry} className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Reessayer
      </Button>

      <div className="mt-8 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
        <p className="text-sm text-slate-400">
          Les donnees precedemment consultees sont disponibles en cache.
          <br />
          Naviguez vers les pages deja visitees pour y acceder.
        </p>
      </div>
    </div>
  );
}
