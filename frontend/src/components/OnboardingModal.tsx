"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Target,
  TrendingUp,
  BarChart3,
  Star,
  Zap,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ONBOARDING_KEY = "paris-sportif-onboarding-completed";

interface OnboardingStep {
  icon: React.ReactNode;
  title: string;
  description: string;
  highlight?: string;
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    icon: <Target className="w-12 h-12 text-primary-500" />,
    title: "Bienvenue sur WinRate AI",
    description:
      "Votre assistant intelligent pour les paris sportifs. Nos modeles ML analysent des milliers de donnees pour vous fournir des predictions fiables.",
    highlight: "Predictions basees sur l'IA",
  },
  {
    icon: <TrendingUp className="w-12 h-12 text-emerald-500" />,
    title: "Score de Confiance",
    description:
      "Chaque prediction affiche un pourcentage de confiance. Plus il est eleve, plus notre modele est sur de sa prediction. Visez les predictions a 70%+ pour de meilleurs resultats.",
    highlight: "70%+ = Haute confiance",
  },
  {
    icon: <Zap className="w-12 h-12 text-amber-500" />,
    title: "Value Bets",
    description:
      "Le score 'Value' indique quand les cotes des bookmakers sont superieures a notre probabilite calculee. C'est la cle pour des paris rentables a long terme.",
    highlight: "Value = Opportunite de profit",
  },
  {
    icon: <BarChart3 className="w-12 h-12 text-blue-500" />,
    title: "Analyse Multi-Modeles",
    description:
      "Nous combinons 4 modeles: Poisson (statistique), ELO (classement), xG (expected goals) et XGBoost (machine learning) pour des predictions robustes.",
    highlight: "4 modeles combines",
  },
  {
    icon: <Star className="w-12 h-12 text-yellow-500" />,
    title: "Daily Picks",
    description:
      "Chaque jour, nous selectionnons les 5 meilleurs paris bases sur le ratio confiance/value. Retrouvez-les dans l'onglet 'Picks' pour ne rien manquer.",
    highlight: "5 picks premium par jour",
  },
];

export function OnboardingModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    // Check if onboarding has been completed
    const completed = localStorage.getItem(ONBOARDING_KEY);
    if (!completed) {
      // Small delay to let the page load first
      const timer = setTimeout(() => setIsOpen(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleComplete = () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    setIsOpen(false);
  };

  const handleSkip = () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    setIsOpen(false);
  };

  const handleNext = () => {
    if (currentStep < ONBOARDING_STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const step = ONBOARDING_STEPS[currentStep];
  const isLastStep = currentStep === ONBOARDING_STEPS.length - 1;

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      // User closed the dialog (via X or clicking outside)
      handleSkip();
    }
    setIsOpen(open);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md p-0 gap-0 overflow-hidden">
        {/* Progress indicator */}
        <div className="flex gap-1.5 px-6 pt-6">
          {ONBOARDING_STEPS.map((_, index) => (
            <div
              key={index}
              className={cn(
                "h-1.5 flex-1 rounded-full transition-colors",
                index <= currentStep
                  ? "bg-primary-500"
                  : "bg-gray-200 dark:bg-slate-700"
              )}
            />
          ))}
        </div>

        {/* Content */}
        <div className="p-6 pt-4">
          <div className="flex flex-col items-center text-center space-y-4">
            {/* Icon */}
            <div className="p-4 rounded-2xl bg-gradient-to-br from-gray-50 to-gray-100 dark:from-slate-800 dark:to-slate-700">
              {step.icon}
            </div>

            {/* Title & Description */}
            <DialogHeader className="space-y-2">
              <DialogTitle className="text-xl font-bold">
                {step.title}
              </DialogTitle>
              <DialogDescription className="text-base leading-relaxed">
                {step.description}
              </DialogDescription>
            </DialogHeader>

            {/* Highlight badge */}
            {step.highlight && (
              <div className="inline-flex px-3 py-1.5 rounded-full bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300 text-sm font-medium">
                {step.highlight}
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between p-6 pt-0 gap-3">
          <Button
            variant="ghost"
            onClick={handlePrev}
            disabled={currentStep === 0}
            className="gap-1"
          >
            <ChevronLeft className="w-4 h-4" />
            Precedent
          </Button>

          <span className="text-sm text-gray-500 dark:text-slate-400">
            {currentStep + 1} / {ONBOARDING_STEPS.length}
          </span>

          <Button onClick={handleNext} className="gap-1">
            {isLastStep ? (
              "Commencer"
            ) : (
              <>
                Suivant
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Hook to reset onboarding (useful for testing)
export function useResetOnboarding() {
  return () => {
    localStorage.removeItem(ONBOARDING_KEY);
    window.location.reload();
  };
}
