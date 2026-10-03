const KEY = "pique_device_fp";

/** Stable anonymous device identity (docs/07 §2; secure enclave once Capacitor). */
export function deviceFp(): string {
  let fp = localStorage.getItem(KEY);
  if (!fp) {
    fp = crypto.randomUUID();
    localStorage.setItem(KEY, fp);
  }
  return fp;
}
