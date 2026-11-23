import type { ReportData } from "./sections";

/**
 * The print route's one data access (Story 13.7, AD-18): the report snapshot, read once from the
 * api inside the network (`API_INTERNAL_URL`, never through the proxy) with its render token.
 * Null for any answer but 200, so the page shows no data.
 */
export async function readSnapshot(snapshotId: string, token: string): Promise<ReportData | null> {
  const base = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  if (!/^[0-9a-f-]{36}$/i.test(snapshotId)) return null;
  try {
    const answer = await fetch(`${base}/api/internal/report-snapshots/${snapshotId}`, {
      headers: { "X-Render-Token": token },
      cache: "no-store",
    });
    if (!answer.ok) return null;
    return (await answer.json()) as ReportData;
  } catch {
    return null;
  }
}
