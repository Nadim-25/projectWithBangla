import { NextRequest, NextResponse } from "next/server";

// ─── Route Definitions ────────────────────────────────────────────────────────

// Accessible without a token
const PUBLIC_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
];

// Requires a valid token but no specific role (any authenticated user)
// Also the ONLY route accessible when requiresPasswordChange = true
const AUTH_ONLY_ROUTES = ["/force-change-password"];

// Requires a valid token AND a specific role
const ROLE_PROTECTED_ROUTES: Record<string, string[]> = {
  "/dashboard": ["user", "admin"],
  "/admin-dashboard": ["admin"],
};

// ─── JWT Decoder ──────────────────────────────────────────────────────────────

interface JwtPayload {
  id: number | string;
  role: string;
  requiresPasswordChange: boolean;
  exp: number;
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const jsonStr = atob(base64);
    return JSON.parse(jsonStr) as JwtPayload;
  } catch {
    return null;
  }
}

function isTokenExpired(payload: JwtPayload): boolean {
  return Date.now() / 1000 > payload.exp;
}

// ─── Proxy ────────────────────────────────────────────────────────────────────

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/"),
  );

  const isAuthOnly = AUTH_ONLY_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/"),
  );

  // Retrieve token from cookie or Authorization header
  const token =
    request.cookies.get("token")?.value ??
    request.headers.get("authorization")?.replace("Bearer ", "");

  // 1. Authenticated user trying to access a public route → redirect appropriately
  if (isPublic) {
    if (token) {
      const payload = decodeJwtPayload(token);
      if (payload && !isTokenExpired(payload)) {
        // Still needs password change → send to force-change-password
        if (payload.requiresPasswordChange) {
          return NextResponse.redirect(
            new URL("/force-change-password", request.url),
          );
        }
        const redirect =
          payload.role === "admin" ? "/admin-dashboard" : "/dashboard";
        return NextResponse.redirect(new URL(redirect, request.url));
      }
    }
    return NextResponse.next();
  }

  // 2. No token on any protected route → redirect to login
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // 3. Decode JWT payload
  const payload = decodeJwtPayload(token);
  if (!payload) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // 4. Expired token → clear cookie and redirect to login
  if (isTokenExpired(payload)) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("token");
    return response;
  }

  // 5. requiresPasswordChange = true → ONLY /force-change-password is allowed
  if (payload.requiresPasswordChange) {
    if (!isAuthOnly) {
      // User tried to navigate anywhere else (e.g. /dashboard via address bar)
      return NextResponse.redirect(
        new URL("/force-change-password", request.url),
      );
    }
  }

  // 6. Auth-only routes → pass through (password already checked above)
  if (isAuthOnly) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-user-id", String(payload.id));
    requestHeaders.set("x-user-role", payload.role);
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  // 7. Role-based route protection
  for (const [route, allowedRoles] of Object.entries(ROLE_PROTECTED_ROUTES)) {
    if (pathname === route || pathname.startsWith(route + "/")) {
      if (!allowedRoles.includes(payload.role)) {
        const redirect =
          payload.role === "admin" ? "/admin-dashboard" : "/dashboard";
        return NextResponse.redirect(new URL(redirect, request.url));
      }
    }
  }

  // 8. Forward user info to Server Components via headers
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-user-id", String(payload.id));
  requestHeaders.set("x-user-role", payload.role);

  return NextResponse.next({ request: { headers: requestHeaders } });
}

// ─── Matcher ──────────────────────────────────────────────────────────────────

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
