// const BASE_URL = "http://localhost:8000/upload";

import { BASE_URL } from "@/settings";

const getToken = () => {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("token="))
    ?.split("=")[1];
};

// ======================================
// GET ALL DOCS
// ======================================
export async function getAllDocs() {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/upload/getalldocs`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to fetch docs");
  }

  return data;
}

// ======================================
// PROCESS DOC
// ======================================
export async function processDoc(docId: number) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/process/${docId}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Process failed");
  }

  return data;
}

// ======================================
// DELETE DOC
// ======================================
export async function deleteDoc(docId: number) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/upload/${docId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Delete failed");
  }

  return data;
}
