import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
export const BACKEND_API_BASE = ((import.meta.env.VITE_BACKEND_API_BASE as string | undefined)
  || (import.meta.env.VITE_BACKEND_URL as string | undefined)
)?.replace(/\/+$/, "") || "";
