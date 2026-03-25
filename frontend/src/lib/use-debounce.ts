import { useEffect, useState } from "react";

/**
 * Debounce a value by `delay` milliseconds.
 * Returns the latest value only after the caller stops changing it
 * for at least `delay` ms.
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);

  return debounced;
}
