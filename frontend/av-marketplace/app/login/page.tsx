'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { ArrowRight, LockKeyhole } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { ApiError, createSession } from '../../lib/api-client';
import { usePlatform } from '../../components/platform/PlatformProvider';

export default function LoginPage() {
  const router = useRouter();
  const { context, refresh } = usePlatform();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createSession(email, password);
      const platform = await refresh();
      if (!platform) {
        throw new ApiError(401, 'Sign-in succeeded but workspace context could not be loaded.');
      }
      router.replace('/platform');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to sign in. Try again.');
    } finally {
      setPending(false);
    }
  }

  useEffect(() => {
    if (context) router.replace('/platform');
  }, [context, router]);

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <span className="login-mark">AV</span>
        <p className="section-kicker">AROGYA VIROHAN PLATFORM</p>
        <h1 id="login-title">Sign in to your workspace</h1>
        <p className="login-copy">Continue to your connected care tools.</p>
        <form className="login-form" onSubmit={submit}>
          <label>Email address<input autoComplete="username" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Password<input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-featured login-submit" type="submit" disabled={pending}>
            <LockKeyhole size={14} />{pending ? 'Signing in…' : 'Sign in'}<ArrowRight size={14} />
          </button>
        </form>
      </section>
    </main>
  );
}