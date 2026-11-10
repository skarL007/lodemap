import { fetcher } from '../lib/fetcher.js';

export async function get() {
  const m = await import('./lazy');
  return fetcher(m);
}
