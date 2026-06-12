import { BASE_URL } from "@/settings";

export async function getMe() {
  const getCookie = (name: string) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop()?.split(";").shift();
    }
    return null;
  };

  const token = getCookie("token");

  if (!token) {
    return null;
  }

  const res = await fetch(`${BASE_URL}/user/is-auth`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    return null;
  }

  return res.json();
}
