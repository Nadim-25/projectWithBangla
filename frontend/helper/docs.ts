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
export async function processDoc(docId: number, force = false) {
  const token = getToken();

  const url = force
    ? `${BASE_URL}/process/${docId}?force=true`
    : `${BASE_URL}/process/${docId}`;

  const res = await fetch(url, {
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
// UPDATE STRATEGY
// ======================================
export async function updateDocStrategy(docId: number, strategy: string) {
  const token = getToken();

  const form = new FormData();
  form.append("chunk_strategy", strategy);

  const res = await fetch(`${BASE_URL}/upload/${docId}/strategy`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Strategy update failed");
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
