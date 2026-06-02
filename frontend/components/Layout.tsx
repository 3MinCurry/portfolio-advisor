import { useUser, UserButton, Protect } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/router";
import { ReactNode, useState } from "react";
import PageTransition from "./PageTransition";

interface LayoutProps {
  children: ReactNode;
}

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "◈" },
  { href: "/accounts", label: "Accounts", icon: "◇" },
  { href: "/advisor-team", label: "Advisors", icon: "◎" },
  { href: "/analysis", label: "Analysis", icon: "◐" },
];

export default function Layout({ children }: LayoutProps) {
  const { user } = useUser();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (path: string) => router.pathname === path;

  return (
    <Protect
      fallback={
        <div className="min-h-screen app-bg flex items-center justify-center">
          <p className="text-muted">Redirecting to sign in...</p>
        </div>
      }
    >
      <div className="min-h-screen app-bg flex">
        {/* Sidebar — desktop */}
        <aside className="hidden lg:flex w-64 flex-col border-r border-border bg-surface/80 backdrop-blur-sm shrink-0">
          <div className="p-6 border-b border-border">
            <Link href="/dashboard" className="block">
              <span className="eyebrow">Alex</span>
              <p className="font-display text-xl font-semibold text-ink mt-1 leading-tight">
                Financial<br />Intelligence
              </p>
            </Link>
          </div>

          <nav className="flex-1 p-4 space-y-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={isActive(item.href) ? "nav-link nav-link-active" : "nav-link"}
              >
                <span className="text-gold text-sm w-5 text-center">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="p-4 border-t border-border">
            <div className="flex items-center gap-3 px-2">
              <UserButton afterSignOutUrl="/" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink truncate">
                  {user?.firstName || "Investor"}
                </p>
                <p className="text-xs text-muted truncate">
                  {user?.emailAddresses[0]?.emailAddress}
                </p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main column */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Mobile header */}
          <header className="lg:hidden sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur-md px-4 py-3 flex items-center justify-between">
            <Link href="/dashboard" className="font-display text-lg font-semibold text-ink">
              Alex
            </Link>
            <button
              type="button"
              onClick={() => setMobileOpen(!mobileOpen)}
              className="btn-ghost p-2"
              aria-label="Menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeWidth={2} d={mobileOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
              </svg>
            </button>
          </header>

          {mobileOpen && (
            <nav className="lg:hidden border-b border-border bg-surface p-4 space-y-1">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={isActive(item.href) ? "nav-link nav-link-active" : "nav-link"}
                >
                  <span className="text-gold">{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </nav>
          )}

          <main className="flex-1 px-4 sm:px-6 lg:px-10 py-8">
            <PageTransition>{children}</PageTransition>
          </main>

          <footer className="border-t border-border px-4 sm:px-6 lg:px-10 py-6 mt-auto">
            <div className="panel-raised p-4 max-w-4xl">
              <p className="text-xs font-semibold text-gold uppercase tracking-wider mb-2">
                Disclaimer
              </p>
              <p className="text-xs text-muted leading-relaxed">
                AI-generated insights are not vetted by a licensed financial advisor and must not be
                used for trading decisions. For informational purposes only.
              </p>
            </div>
            <p className="text-xs text-muted text-center mt-4">
              Alex · Multi-agent portfolio intelligence
            </p>
          </footer>
        </div>
      </div>
    </Protect>
  );
}
