/**
 * Debug logging utilities
 * Only logs in development mode or when DEBUG env var is set
 */

const isDev = process.env.NODE_ENV === "development";
const isDebug = process.env.NEXT_PUBLIC_DEBUG === "true";

interface DebugOptions {
  prefix?: string;
  enabled?: boolean;
}

function shouldLog(options?: DebugOptions): boolean {
  if (options?.enabled !== undefined) {
    return options.enabled;
  }
  return isDev || isDebug;
}

function formatMessage(prefix: string | undefined, ...args: unknown[]): unknown[] {
  if (prefix) {
    return [`[${prefix}]`, ...args];
  }
  return args;
}

/**
 * Debug logger - only logs in development or when DEBUG is enabled
 */
export const debug = {
  log: (options: DebugOptions | string, ...args: unknown[]) => {
    const opts = typeof options === "string" ? { prefix: options } : options;
    if (shouldLog(opts)) {
      console.log(...formatMessage(opts.prefix, ...args));
    }
  },

  warn: (options: DebugOptions | string, ...args: unknown[]) => {
    const opts = typeof options === "string" ? { prefix: options } : options;
    if (shouldLog(opts)) {
      console.warn(...formatMessage(opts.prefix, ...args));
    }
  },

  error: (options: DebugOptions | string, ...args: unknown[]) => {
    const opts = typeof options === "string" ? { prefix: options } : options;
    // Errors always log regardless of debug mode
    console.error(...formatMessage(opts.prefix, ...args));
  },

  info: (options: DebugOptions | string, ...args: unknown[]) => {
    const opts = typeof options === "string" ? { prefix: options } : options;
    if (shouldLog(opts)) {
      console.info(...formatMessage(opts.prefix, ...args));
    }
  },
};

/**
 * Create a scoped debug logger with a fixed prefix
 */
export function createDebugLogger(prefix: string, enabled?: boolean) {
  return {
    log: (...args: unknown[]) => debug.log({ prefix, enabled }, ...args),
    warn: (...args: unknown[]) => debug.warn({ prefix, enabled }, ...args),
    error: (...args: unknown[]) => debug.error({ prefix, enabled }, ...args),
    info: (...args: unknown[]) => debug.info({ prefix, enabled }, ...args),
  };
}

// Pre-configured loggers for common modules
export const authLogger = createDebugLogger("Auth");
export const pwaLogger = createDebugLogger("PWA");
export const queryLogger = createDebugLogger("Query");
