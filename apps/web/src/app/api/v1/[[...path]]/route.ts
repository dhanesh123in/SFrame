import { NextRequest, NextResponse } from "next/server";

const API_URL = (process.env.API_URL ?? "http://127.0.0.1:8100").replace(/\/$/, "");

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path?: string[] }> };

async function proxy(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { path = [] } = await context.params;
  const targetPath = path.length ? path.join("/") : "";
  const url = new URL(`${API_URL}/api/v1/${targetPath}`);
  url.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");

  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  const upstream = await fetch(url.toString(), {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    // @ts-expect-error duplex required for streaming request bodies in Node
    duplex: hasBody ? "half" : undefined,
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("transfer-encoding");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
