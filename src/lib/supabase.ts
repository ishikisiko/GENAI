import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export const EDGE_FN_BASE = `${supabaseUrl}/functions/v1`;

export const edgeHeaders = {
  apikey: supabaseAnonKey,
  Authorization: `Bearer ${supabaseAnonKey}`,
  "Content-Type": "application/json",
};
