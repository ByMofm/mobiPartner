import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || "";

async function proxyRequest(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = `/api/${path.join("/")}`;
  const url = new URL(apiPath, BACKEND_URL);

  // Forward query params
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.append(key, value);
  });

  // Use admin key for /scrape/* routes, regular key for everything else
  const isAdminRoute = path[0] === "scrape";
  const key = isAdminRoute ? (ADMIN_API_KEY || API_KEY) : API_KEY;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (key) {
    headers["X-API-Key"] = key;
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    try {
      const body = await request.text();
      if (body) init.body = body;
    } catch {
      // no body
    }
  }

  try {
    const res = await fetch(url.toString(), init);
    const data = await res.text();

    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Backend unavailable", detail: String(error) },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
