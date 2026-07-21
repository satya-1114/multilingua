/**
 * Client-side error reporting stub.
 *
 * Wires into the platform's observability pipeline. Kept as a no-op until a
 * concrete reporter (e.g. Sentry, Datadog RUM) is configured, so imports and
 * boundaries continue to work without a hard dependency on any vendor.
 */

export type ErrorReportContext = Record<string, unknown>;

export function reportClientError(_error: unknown, _context: ErrorReportContext = {}) {
  // Intentional no-op. Replace with a real transport when observability is provisioned.
}
