/** Display aliases keep historic runtime identifiers readable without changing data. */
export const ORCHESTRATOR_LABEL = "Orquestrador";

export function formatDisplayTerminology(value: string): string {
  return value.replace(/(^|[^\p{L}\p{N}])supervisor(es|s)?(?=$|[^\p{L}\p{N}])/giu, (match, prefix: string, plural?: string) => {
    const original = match.slice(prefix.length);
    const replacement = plural ? "orquestradores" : "orquestrador";
    const label = original === original.toUpperCase()
      ? replacement.toUpperCase()
      : original[0] === original[0].toUpperCase()
        ? replacement[0].toUpperCase() + replacement.slice(1)
        : replacement;
    return prefix + label;
  });
}
