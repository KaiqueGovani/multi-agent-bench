import { CorrectedComparisonView } from "@/components/runtime/corrected-comparison-view";
import { loadCorrectedComparison } from "@/lib/corrected-comparison/results";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function CorrectedComparisonPage() {
  return <CorrectedComparisonView data={await loadCorrectedComparison()} />;
}
