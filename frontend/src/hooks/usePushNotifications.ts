import { useCallback, useEffect, useState } from "react";

type Permission = "granted" | "denied" | "default" | "unsupported";

const STORAGE_KEY = "push_notifications_enabled";

export function usePushNotifications() {
  const [permission, setPermission] = useState<Permission>(() => {
    if (typeof Notification === "undefined") return "unsupported";
    return Notification.permission as Permission;
  });

  const [enabled, setEnabled] = useState<boolean>(() => {
    return localStorage.getItem(STORAGE_KEY) === "1";
  });

  useEffect(() => {
    if (typeof Notification === "undefined") return;
    setPermission(Notification.permission as Permission);
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (typeof Notification === "undefined") return false;
    if (Notification.permission === "granted") {
      setPermission("granted");
      setEnabled(true);
      localStorage.setItem(STORAGE_KEY, "1");
      return true;
    }
    const result = await Notification.requestPermission();
    setPermission(result as Permission);
    if (result === "granted") {
      setEnabled(true);
      localStorage.setItem(STORAGE_KEY, "1");
      return true;
    }
    return false;
  }, []);

  const disable = useCallback(() => {
    setEnabled(false);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const toggle = useCallback(async () => {
    if (enabled) {
      disable();
    } else {
      await requestPermission();
    }
  }, [enabled, disable, requestPermission]);

  const notify = useCallback(
    (title: string, body: string, tag?: string) => {
      if (!enabled || permission !== "granted") return;
      try {
        new Notification(title, {
          body,
          icon: "/vite.svg",
          tag,
          dir: "rtl",
          lang: "he",
        });
      } catch {
        // Notification API not available in this context
      }
    },
    [enabled, permission]
  );

  const isSupported = typeof Notification !== "undefined";

  return { permission, enabled, isSupported, toggle, notify, requestPermission, disable };
}
