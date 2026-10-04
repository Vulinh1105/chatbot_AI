import { useEffect } from "react";
import { getCurrentUser } from "../../services/authService";
import { useAuthStore } from "../../stores/authStore";

function AuthInitializer() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const login = useAuthStore((state) => state.login);
  const setInitializing = useAuthStore((state) => state.setInitializing);

  useEffect(() => {
    if (!accessToken) {
      setInitializing(false);
      return;
    }

    const restoreSession = async () => {
      try {
        const user = await getCurrentUser();
        login(user, accessToken);
      } catch {
        useAuthStore.getState().logout();
      }
    };

    restoreSession();
  }, [accessToken, login, setInitializing]);

  return null;
}

export default AuthInitializer;