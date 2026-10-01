export function formatLocator(locator: Record<string, string | null> | undefined): string {
  if (!locator) return "";
  const parts: string[] = [];
  if (locator.page != null && locator.page !== "") parts.push(`page ${locator.page}`);
  if (locator.section) parts.push(`section ${locator.section}`);
  if (locator.path) parts.push(`path ${locator.path}`);
  return parts.join(", ");
}
