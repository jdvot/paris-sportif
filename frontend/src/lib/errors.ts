/**
 * Type guard to check if an error has a message property
 */
export function isErrorWithMessage(error: unknown): error is { message: string } {
  return (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof (error as Record<string, unknown>).message === "string"
  );
}

/**
 * Extract error message from unknown error type
 */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (isErrorWithMessage(error)) {
    return error.message;
  }
  return fallback;
}
