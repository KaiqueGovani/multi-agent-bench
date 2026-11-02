import { readCorrectedComparisonArtifact } from "@/lib/corrected-comparison/results";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_request: Request, { params }: { params: Promise<{ filename: string }> }) {
  const { filename } = await params;
  const artifact = await readCorrectedComparisonArtifact(filename);
  if (!artifact) return new Response("Arquivo público indisponível.", { status: 404, headers: { "Cache-Control": "no-store" } });
  return new Response(new Uint8Array(artifact.data), { headers: {
    "Content-Type": artifact.contentType,
    "Content-Disposition": `${artifact.contentType.startsWith("image/") ? "inline" : "attachment"}; filename="${filename}"`,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "sandbox; default-src 'none'",
  } });
}
