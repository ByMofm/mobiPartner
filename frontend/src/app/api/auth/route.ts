import { NextRequest, NextResponse } from "next/server";
import { SignJWT, jwtVerify } from "jose";

const AUTH_PASSWORD = process.env.AUTH_PASSWORD || "";
const AUTH_SECRET = new TextEncoder().encode(
  process.env.AUTH_SECRET || "dev-secret-change-in-production"
);

export async function POST(request: NextRequest) {
  try {
    const { password } = await request.json();

    if (!AUTH_PASSWORD) {
      // Auth disabled in dev when no password is configured
      const token = await new SignJWT({ sub: "admin" })
        .setProtectedHeader({ alg: "HS256" })
        .setExpirationTime("7d")
        .sign(AUTH_SECRET);

      const response = NextResponse.json({ ok: true });
      response.cookies.set("session", token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: "/",
      });
      return response;
    }

    if (password !== AUTH_PASSWORD) {
      return NextResponse.json({ error: "Contrasena incorrecta" }, { status: 401 });
    }

    const token = await new SignJWT({ sub: "admin" })
      .setProtectedHeader({ alg: "HS256" })
      .setExpirationTime("7d")
      .sign(AUTH_SECRET);

    const response = NextResponse.json({ ok: true });
    response.cookies.set("session", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
      path: "/",
    });
    return response;
  } catch {
    return NextResponse.json({ error: "Bad request" }, { status: 400 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete("session");
  return response;
}
