"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";
import { logger } from "@/lib/logger";

interface ErrorBoundaryTranslations {
  errorTitle: string;
  errorDescription: string;
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  translations?: ErrorBoundaryTranslations;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error("ErrorBoundary caught an error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { translations } = this.props;
      const errorTitle = translations?.errorTitle ?? "Erreur de chargement";
      const errorDescription = translations?.errorDescription ?? "Ce composant n'a pas pu etre affiche.";

      return (
        <div role="alert" className="p-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-red-800 dark:text-red-300 text-sm">
                {errorTitle}
              </h3>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                {errorDescription}
              </p>
              {process.env.NODE_ENV === "development" && this.state.error && (
                <p className="text-xs font-mono text-red-500 dark:text-red-400 mt-2 break-all">
                  {this.state.error.message}
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={this.handleReset}
              className="flex-shrink-0 text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Wrapper component that provides translations via hooks
export function LocalizedErrorBoundary({
  children,
  fallback,
  onError,
}: Omit<Props, "translations">) {
  const t = useTranslations("common");

  return (
    <ErrorBoundary
      fallback={fallback}
      onError={onError}
      translations={{
        errorTitle: t("errorLoading"),
        errorDescription: t("componentError"),
      }}
    >
      {children}
    </ErrorBoundary>
  );
}

// HOC for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
) {
  return function WithErrorBoundaryWrapper(props: P) {
    return (
      <LocalizedErrorBoundary fallback={fallback}>
        <WrappedComponent {...props} />
      </LocalizedErrorBoundary>
    );
  };
}
