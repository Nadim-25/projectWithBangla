import { BASE_URL } from "@/settings";

// const BASE_URL = "http://localhost:8000/user";
BASE_URL;
export async function getAllUsers() {
  const token = document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];

  const res = await fetch(`${BASE_URL}/user/all-users`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to fetch users");
  }

  return data;
}

const getToken = () => {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];
};

// ======================================
// TOGGLE ACTIVE
// ======================================
export async function toggleUserActive(userId: number) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/user/toggle-active/${userId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to update");
  }

  return data;
}

// ======================================
// TOGGLE VERIFIED
// ======================================
export async function toggleUserVerified(userId: number) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/user/toggle-verified/${userId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to update");
  }

  return data;
}

// ======================================
// ADMIN SUMMARY
// ======================================
export async function getAdminSummary() {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/user/admin-summary`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to fetch summary");
  }

  return data as {
    users: {
      total: number;
      active: number;
      inactive: number;
      verified: number;
      unverified: number;
      admins: number;
      regular: number;
    };
    documents: {
      total: number;
      processed: number;
      unprocessed: number;
    };
  };
}

// ======================================
// REGISTER / ADD USER BY ADMIN
// ======================================
export async function registerUser(data: {
  fullName: string;
  userName: string;
  email: string;
  hashedPassword: string;
  confirmHashedPassword: string;
}) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/user/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  const result = await res.json();

  if (!res.ok) {
    throw new Error(result.detail || "Failed to register user");
  }

  return result;
}

// ======================================
// UPDATE USER BY ADMIN
// ======================================
export async function updateUser(
  userId: number,
  data: {
    fullName: string;
    userName: string;
    email: string;
    role: string;
    division: string;
    department: string;
  },
) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/user/update-user/${userId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  const result = await res.json();

  if (!res.ok) {
    throw new Error(result.detail || "Failed to update user");
  }

  return result;
}

// ======================================
// RESET PASSWORD BY ADMIN
// ======================================
export async function resetPasswordByAdmin(
  userId: number,
  password: string,
  confirmPassword: string,
) {
  const token = getToken();

  const res = await fetch(
    `${BASE_URL}/user/password-change-byadmin/${userId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        password,
        confirmPassword,
      }),
    },
  );

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Password reset failed");
  }

  return data;
}
