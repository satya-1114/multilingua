/**
 * Runtime validators for API payloads. Zod-friendly seams — a project can
 * upgrade to full schemas without touching call sites.
 */

export type Validator<T> = (input: unknown) => T;

export function assertObject(input: unknown, message = "Expected object"): Record<string, unknown> {
  if (!input || typeof input !== "object") throw new Error(message);
  return input as Record<string, unknown>;
}

export function assertString(input: unknown, field: string): string {
  if (typeof input !== "string") throw new Error(`Field ${field} must be a string`);
  return input;
}

export function assertNumber(input: unknown, field: string): number {
  if (typeof input !== "number" || Number.isNaN(input)) throw new Error(`Field ${field} must be a number`);
  return input;
}

export function optional<T>(fn: Validator<T>): Validator<T | undefined> {
  return (input) => (input === undefined || input === null ? undefined : fn(input));
}
