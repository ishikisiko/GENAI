import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface GenerateAgentsRequest {
  case_id?: string;
}

function successResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
  });
}

function errorResponse(message: string, status = 400, details?: unknown): Response {
  return new Response(
    JSON.stringify({
      error: {
        code: "EDGE_COMPAT_ERROR",
        message,
        details,
      },
    }),
    {
      status,
      headers: {
        ...corsHeaders,
        "Content-Type": "application/json",
      },
    },
  );
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return errorResponse("Method not allowed", 405);
  }

  try {
    let body: GenerateAgentsRequest;
    try {
      body = await req.json() as GenerateAgentsRequest;
    } catch {
      return errorResponse("Invalid JSON body", 400);
    }

    if (!body.case_id) {
      return errorResponse("case_id is required", 400);
    }

    const backendBase = (Deno.env.get("BACKEND_API_BASE") || "").replace(/\/+$/, "");
    if (!backendBase) {
      return errorResponse(
        "Python backend is not configured for generate-agents compatibility forwarding",
        501,
        "Set BACKEND_API_BASE for this Edge Function, or call /api/agent-generation directly from the frontend",
      );
    }

    const backendResponse = await fetch(`${backendBase}/api/agent-generation`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ case_id: body.case_id }),
    });

    const payload = await backendResponse.json();
    return successResponse(payload, backendResponse.status);
  } catch (err) {
    return errorResponse(String(err), 500);
  }
});
