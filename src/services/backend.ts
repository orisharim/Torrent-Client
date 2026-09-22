/**
 * Await `promise`; return `fallback()` if it rejects (no Tauri runtime) or if it
 * resolves to an empty array (backend stub returning nothing yet).
 */
export const withFallback = async <T>(promise: Promise<T>, fallback: () => T): Promise<T> => {
  try {
    const result = await promise;
    if (Array.isArray(result) && result.length === 0) return fallback();
    return result;
  } catch (error) {
    console.warn("[backend unavailable — using demo fallback]", error);
    return fallback();
  }
};

/** Fire-and-forget mutation: never let a missing backend surface as an unhandled rejection. */
export const safeCall = (promise: Promise<unknown>): Promise<void> =>
  promise.then(() => undefined).catch((error) => {
    console.warn("[backend unavailable]", error);
  });
