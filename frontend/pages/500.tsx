import Link from 'next/link';
import Head from 'next/head';

export default function Custom500() {
  return (
    <>
      <Head>
        <title>500 — Alex</title>
      </Head>
      <div className="min-h-screen app-bg flex items-center justify-center px-4">
        <div className="text-center panel p-12 max-w-md">
          <p className="eyebrow text-coral mb-2">Error</p>
          <h1 className="font-display text-6xl font-semibold text-coral mb-2">500</h1>
          <h2 className="text-xl text-ink mb-4">Server error</h2>
          <p className="text-muted mb-8 text-sm">Something went wrong. Please try again later.</p>
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
