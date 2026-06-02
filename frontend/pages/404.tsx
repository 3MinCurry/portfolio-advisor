import Link from 'next/link';
import Head from 'next/head';

export default function Custom404() {
  return (
    <>
      <Head>
        <title>404 — Alex</title>
      </Head>
      <div className="min-h-screen app-bg flex items-center justify-center px-4">
        <div className="text-center panel p-12 max-w-md">
          <p className="eyebrow mb-2">Error</p>
          <h1 className="font-display text-6xl font-semibold text-gold mb-2">404</h1>
          <h2 className="text-xl text-ink mb-4">Page not found</h2>
          <p className="text-muted mb-8 text-sm">
            The page you are looking for does not exist or has been moved.
          </p>
          <Link href="/dashboard">
            <button type="button" className="btn btn-primary">
              Return to dashboard
            </button>
          </Link>
        </div>
      </div>
    </>
  );
}
