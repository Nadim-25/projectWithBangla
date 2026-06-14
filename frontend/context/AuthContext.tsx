"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";

import { usePathname, useRouter } from "next/navigation";
import { useFlash } from "@/context/FlashContext";

import { getMe } from "@/lib/auth";

type UserType = {
  id: number;
  fullName: string;
  email: string;
  role: string;
};

type AuthContextType = {
  user: UserType | null;
  loading: boolean;
  refreshUser: () => Promise<void>;
  logout: () => void;
};

const publicRoutes = [
  "/login",
  "/register",
];

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);

  const pathname = usePathname();
  const router = useRouter();
  const { showFlash } = useFlash();

  // =========================================
  // CHECK IF CURRENT ROUTE IS PUBLIC
  // =========================================
  const isPublicRoute = publicRoutes.some((route) =>
    pathname.startsWith(route),
  );

  // =========================================
  // LOGOUT
  // =========================================
  const logout = useCallback(() => {
    document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    setUser(null);
    showFlash("You have been logged out successfully.", "info");
    router.push("/login");
  }, [router, showFlash]);

  // =========================================
  // REFRESH USER
  // =========================================
  const refreshUser = useCallback(async () => {
    // skip auth check on public routes
    if (isPublicRoute) {
      setLoading(false);
      return;
    }

    try {
      const data = await getMe();

      console.log("AUTH USER:", data);

      if (!data) {
        logout();
        return;
      }

      setUser(data);
    } catch (err) {
      console.error("REFRESH USER ERROR:", err);

      logout();
    } finally {
      setLoading(false);
    }
  }, [logout, isPublicRoute]);

  // =========================================
  // INITIAL AUTH CHECK
  // =========================================
  useEffect(() => {
    // skip auth on public routes
    if (isPublicRoute) {
      setLoading(false);
      return;
    }

    let mounted = true;

    const loadUser = async () => {
      try {
        const data = await getMe();

        console.log("INITIAL USER:", data);

        if (!mounted) return;

        if (!data) {
          logout();
          return;
        }

        setUser(data);
      } catch (err) {
        console.error("INITIAL AUTH ERROR:", err);

        if (mounted) {
          logout();
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadUser();

    return () => {
      mounted = false;
    };
  }, [logout, isPublicRoute]);

  // =========================================
  // AUTO TOKEN VALIDITY CHECK
  // =========================================
  useEffect(() => {
    // no interval on public routes
    if (isPublicRoute) return;

    const interval = setInterval(async () => {
      try {
        const data = await getMe();

        console.log("TOKEN CHECK:", data);

        // token expired
        if (!data) {
          logout();
        }
      } catch (err) {
        console.error("TOKEN CHECK ERROR:", err);

        logout();
      }
    }, 60000); // every 1 minute

    return () => clearInterval(interval);
  }, [logout, isPublicRoute]);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        refreshUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// =========================================
// CUSTOM HOOK
// =========================================
export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
};

// "use client";
// import { usePathname } from "next/navigation";

// import {
//   createContext,
//   useContext,
//   useEffect,
//   useState,
//   useCallback,
// } from "react";

// import { useRouter } from "next/navigation";

// import { getMe } from "@/lib/auth";

// type AuthContextType = {
//   user: any;
//   loading: boolean;
//   refreshUser: () => Promise<void>;
//   logout: () => void;
// };

// const publicRoutes = [
//   "/login",
//   "/register",
//   "/forgot-password",
//   "/reset-password",
// ];

// const AuthContext = createContext<AuthContextType | null>(null);

// export function AuthProvider({ children }: { children: React.ReactNode }) {
//   const [user, setUser] = useState<any>(null);
//   const [loading, setLoading] = useState(true);
//   const pathname = usePathname();
//   const router = useRouter();

//   // =========================
//   // LOGOUT
//   // =========================
//   const logout = useCallback(() => {
//     // remove token cookie
//     document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

//     setUser(null);

//     router.push("/login");
//   }, [router]);

//   // =========================
//   // REFRESH USER
//   // =========================
//   const refreshUser = useCallback(async () => {
//     // ✅ skip auth check on public pages
//     if (isPublicRoute) {
//       setLoading(false);
//       return;
//     }

//     try {
//       const data = await getMe();

//       if (!data) {
//         logout();
//         return;
//       }

//       setUser(data);
//     } catch (err) {
//       console.error(err);

//       logout();
//     } finally {
//       setLoading(false);
//     }
//   }, [logout, isPublicRoute]);
//   // =========================
//   // INITIAL AUTH CHECK
//   // =========================

//   useEffect(() => {
//     // ✅ skip auth check on public routes
//     if (isPublicRoute) {
//       setLoading(false);
//       return;
//     }

//     let mounted = true;

//     const loadUser = async () => {
//       try {
//         const data = await getMe();

//         if (!mounted) return;

//         if (!data) {
//           logout();
//           return;
//         }

//         setUser(data);
//       } catch (err) {
//         console.error(err);

//         if (mounted) {
//           logout();
//         }
//       } finally {
//         if (mounted) {
//           setLoading(false);
//         }
//       }
//     };

//     loadUser();

//     return () => {
//       mounted = false;
//     };
//   }, [logout, isPublicRoute]);

// =========================
// AUTO TOKEN VALIDITY CHECK
// =========================
// useEffect(() => {
//   const interval = setInterval(async () => {
//     try {
//       const data = await getMe();

//       // token expired
//       if (!data) {
//         logout();
//       }
//     } catch (err) {
//       console.error(err);

//       logout();
//     }
//   }, 60000); // every 1 minute

//   return () => clearInterval(interval);
// }, [logout]);

//   useEffect(() => {
//     // ✅ no interval on public routes
//     if (isPublicRoute) return;

//     const interval = setInterval(async () => {
//       try {
//         const data = await getMe();
//         console.log("GET ME DATA:", data);
//         if (!data) {
//           logout();
//         }
//       } catch (err) {
//         console.error(err);

//         logout();
//       }
//     }, 60000);

//     return () => clearInterval(interval);
//   }, [logout, isPublicRoute]);
//   return (
//     <AuthContext.Provider
//       value={{
//         user,
//         loading,
//         refreshUser,
//         logout,
//       }}
//     >
//       {children}
//     </AuthContext.Provider>
//   );
// }

// export const useAuth = () => {
//   const context = useContext(AuthContext);

//   if (!context) {
//     throw new Error("useAuth must be used inside AuthProvider");
//   }

//   return context;
// };

// "use client";

// import { createContext, useContext, useEffect, useState } from "react";

// import { getMe } from "@/lib/auth";

// const AuthContext = createContext<any>(null);

// export function AuthProvider({ children }: { children: React.ReactNode }) {
//   const [user, setUser] = useState<any>(null);
//   const [loading, setLoading] = useState(true);

//   // reusable function
//   const refreshUser = async () => {
//     try {
//       const data = await getMe();

//       setUser(data);
//     } catch (err) {
//       console.error(err);
//       setUser(null);
//     } finally {
//       setLoading(false);
//     }
//   };

//   // ✅ FIXED EFFECT
//   useEffect(() => {
//     let mounted = true;

//     const loadUser = async () => {
//       try {
//         const data = await getMe();

//         if (mounted) {
//           setUser(data);
//         }
//       } catch (err) {
//         console.error(err);

//         if (mounted) {
//           setUser(null);
//         }
//       } finally {
//         if (mounted) {
//           setLoading(false);
//         }
//       }
//     };

//     loadUser();

//     return () => {
//       mounted = false;
//     };
//   }, []);

//   return (
//     <AuthContext.Provider
//       value={{
//         user,
//         loading,
//         refreshUser,
//       }}
//     >
//       {children}
//     </AuthContext.Provider>
//   );
// }

// export const useAuth = () => useContext(AuthContext);

// "use client";

// import { createContext, useContext, useEffect, useState } from "react";

// import { getMe } from "@/lib/auth";
// import { useRouter } from "next/navigation";

// const AuthContext = createContext<any>(null);

// export function AuthProvider({ children }: { children: React.ReactNode }) {
//   const router = useRouter();

//   const [user, setUser] = useState<any>(null);
//   const [loading, setLoading] = useState(true);

//   // logout function
//   const logout = () => {
//     document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";

//     setUser(null);

//     router.push("/login");
//   };

//   // reusable function
//   const refreshUser = async () => {
//     try {
//       const data = await getMe();

//       if (!data) {
//         logout();
//         return;
//       }

//       setUser(data);
//     } catch (error) {
//       logout();
//     } finally {
//       setLoading(false);
//     }
//   };

//   // initial auth check
//   useEffect(() => {
//     refreshUser();
//   }, []);

//   // auto session check every minute
//   useEffect(() => {
//     const interval = setInterval(async () => {
//       const data = await getMe();

//       if (!data) {
//         logout();
//       }
//     }, 20000);

//     return () => clearInterval(interval);
//   }, []);

//   return (
//     <AuthContext.Provider
//       value={{
//         user,
//         loading,
//         refreshUser,
//         logout,
//       }}
//     >
//       {children}
//     </AuthContext.Provider>
//   );
// }

// export const useAuth = () => useContext(AuthContext);
