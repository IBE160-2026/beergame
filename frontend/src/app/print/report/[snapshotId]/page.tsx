import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { reportCopy } from "../copy";
import { Report } from "../report";
import { readSnapshot } from "../snapshot";

/**
 * The Student report page (Story 13.7, FR-58, AD-18, UX-DR68): `worker-batch` fetches it with the
 * snapshot's render token and converts it with WeasyPrint (`pdf/ua-1`) to a tagged PDF. It is
 * rendered on the server and needs no JavaScript; it reads only that snapshot, once, with the
 * token (`/api/internal/report-snapshots/{id}`), and a used, expired or wrong token answers 404
 * with no data. The proxy answers 404 for `/print/*` (AD-11). Fonts are the root layout's
 * self-hosted Source Sans 3. The header is the report's skeleton; each section renders through the
 * registry in `../sections.tsx`.
 */
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: reportCopy.title,
  robots: { index: false },
};

type Props = {
  params: Promise<{ snapshotId: string }>;
  searchParams: Promise<{ token?: string | string[] }>;
};

export default async function ReportPrintPage({ params, searchParams }: Props) {
  const { snapshotId } = await params;
  const { token } = await searchParams;
  const data = typeof token === "string" ? await readSnapshot(snapshotId, token) : null;
  if (!data) notFound();
  return <Report data={data} />;
}
