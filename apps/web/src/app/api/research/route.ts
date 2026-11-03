import { NextRequest, NextResponse } from "next/server";
import { getResearchMemory } from "@/lib/research/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const noStore = { "Cache-Control": "no-store" };

export async function GET(request: NextRequest) {
  const store = getResearchMemory(request.headers);
  if (!store)
    return NextResponse.json({ error: "Não encontrado." }, { status: 404, headers: noStore });
  try {
    const { data, details } = await store;
    const runId = request.nextUrl.searchParams.get("run");
    const value = runId ? details.get(runId) : data;
    if (!value)
      return NextResponse.json(
        { error: "Execução não encontrada." },
        { status: 404, headers: noStore },
      );
    return NextResponse.json(value, {
      headers: {
        ...noStore,
        "X-MAB-Mode": "read-only-memory",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Não foi possível carregar a consulta local." },
      { status: 503, headers: noStore },
    );
  }
}
