export const DOMAIN_LABEL: Record<string, string> = {
  solid: "Solid fuel",
  gas: "Gas flame",
  liquid_droplet: "Liquid droplet",
  aerosol_smoke: "Smoke",
  mixed: "Mixed",
  unknown: "Unknown",
};

export const DOMAIN_OPTIONS = [
  { value: "solid", label: "Solid", icon: "view_in_ar" },
  { value: "gas", label: "Gas", icon: "air" },
  { value: "liquid_droplet", label: "Liquid", icon: "water_drop" },
  { value: "aerosol_smoke", label: "Smoke", icon: "blur_on" },
] as const;

export const GRAVITY_LABEL: Record<string, string> = {
  microgravity: "μg Space",
  normal_gravity: "Earth 1g",
  partial_gravity: "Partial gravity",
  unknown: "Unknown gravity",
};

/** The main measured result we chart for each fuel type. */
export const OUTCOME_BY_DOMAIN: Record<string, { field: string; label: string; unit: string }> = {
  solid: { field: "flame_spread_rate", label: "Flame spread rate", unit: "mm/s" },
  gas: { field: "flame_height", label: "Flame length", unit: "mm" },
  liquid_droplet: { field: "burning_rate", label: "Burning rate", unit: "mm²/s" },
  aerosol_smoke: { field: "smoke_particle_size", label: "Smoke particle size", unit: "µm" },
};

export const FIELD_LABEL: Record<string, string> = {
  flame_spread_rate: "Flame spread rate",
  ignition_delay: "Ignition delay",
  flame_height: "Flame length",
  extinction_condition: "Extinction point",
  soot_metric: "Soot / smoke measure",
  heat_flux: "Heat / radiation",
  burning_rate: "Burning rate",
  smoke_particle_size: "Smoke particle size",
  oxygen_fraction: "Oxygen",
  pressure: "Pressure",
  flow_velocity: "Airflow speed",
};

export const MISSING_TEXT: Record<string, string> = {
  not_reported: "The source did not report this value.",
  not_measured: "This was not measured in this test.",
  not_applicable: "This measurement does not apply to this kind of test.",
  unavailable_in_source: "The value is missing from the source data.",
  parsing_failed: "The value could not be read from the source file.",
};

export function fieldLabel(field: string): string {
  return FIELD_LABEL[field] ?? field.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function missingText(reason?: string | null): string {
  return (reason && MISSING_TEXT[reason]) || "This value was not recorded.";
}

/** Rounds without trailing zeros: 1.50 -> "1.5", 101.3 -> "101.3". */
export function num(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v.toFixed(digits)).toString();
}

export function pct(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined) return "—";
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function yearWindow(start?: string | null, end?: string | null): string {
  const s = start?.slice(0, 4);
  const e = end?.slice(0, 4);
  if (s && e) return s === e ? s : `${s} – ${e}`;
  return s || e || "—";
}

export function shortHash(hash?: string | null): string {
  if (!hash) return "—";
  return hash.length > 20 ? `${hash.slice(0, 10)}…${hash.slice(-6)}` : hash;
}

export function doiUrl(doi: string): string {
  return `https://doi.org/${doi}`;
}

export function bytes(n: number): string {
  return n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KB`;
}
