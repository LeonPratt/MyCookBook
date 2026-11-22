export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    headers:
      data instanceof FormData
        ? undefined
        : { "Content-Type": "application/json" },
    body:
      data === undefined
        ? undefined
        : data instanceof FormData
          ? data
          : JSON.stringify(data),
  });
  if (!response.ok) {
    const e = await response
      .json()
      .catch(() => ({ error: "Server could not be reached" }));
    throw new Error(
      e.error +
        (e.details
          ? " — " +
            e.details
              .map(
                (d: { field: string; message: string }) =>
                  `${d.field}: ${d.message}`,
              )
              .join("; ")
          : ""),
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function formatQuantity(
  quantity: number | null,
  selected: number,
  base: number,
): string {
  if (quantity === null) return "";
  const n = (quantity * selected) / base;
  if (!Number.isFinite(n)) return "";
  if (n === 0) return "0";
  const whole = Math.floor(n),
    fraction = n - whole;
  const fractions: [[number, string], ...Array<[number, string]>] = [
    [0.125, "⅛"],
    [0.25, "¼"],
    [1 / 3, "⅓"],
    [0.5, "½"],
    [2 / 3, "⅔"],
    [0.75, "¾"],
  ];
  const match = fractions.find(([v]) => Math.abs(v - fraction) < 0.00001);
  if (match) return (whole ? `${whole} ` : "") + match[1];
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: n < 0.01 ? 6 : 2,
  }).format(n);
}
