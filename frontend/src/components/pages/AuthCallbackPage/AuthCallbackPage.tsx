import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { exchangeCode, getMe } from '@/shared/api';

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setToken, setUser } = useAuthStore();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const storedState = sessionStorage.getItem('oauth_state');

    if (!code || !state || state !== storedState) {
      navigate('/', { replace: true });
      return;
    }

    sessionStorage.removeItem('oauth_state');

    exchangeCode(code)
      .then((token) => {
        setToken(token);
        return getMe();
      })
      .then((u) => {
        setUser({
          id: u.id,
          email: u.email,
          displayName: u.display_name,
          avatarUrl: u.avatar_url,
        });
        navigate('/chat', { replace: true });
      })
      .catch(() => {
        navigate('/', { replace: true });
      });
  }, [navigate, searchParams, setToken, setUser]);

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <svg className="h-8 w-8 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p className="text-sm text-muted-foreground">Signing you in…</p>
      </div>
    </div>
  );
}
