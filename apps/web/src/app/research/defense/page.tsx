import type { Metadata } from "next";
import summary from "../../../../../../research-data/results/matrix40-v1-final/results-summary.json";
import { DefensePresentation } from "./presentation";

export const metadata: Metadata = { title: "Defesa do TCC · MAB · coleta histórica" };
export default function DefensePage() {
  return <DefensePresentation data={summary} />;
}
