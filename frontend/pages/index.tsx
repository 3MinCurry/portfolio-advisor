import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import Head from "next/head";

const AGENTS = [
  { glyph: "◎", name: "Orchestrator", role: "Coordinates every analysis run", accent: "text-gold" },
  { glyph: "◈", name: "Portfolio Analyst", role: "Holdings, performance, narrative report", accent: "text-sage" },
  { glyph: "◇", name: "Chart Specialist", role: "Allocation and exposure visualizations", accent: "text-violet" },
  { glyph: "△", name: "Risk Manager", role: "Concentration and diversification review", accent: "text-coral" },
  { glyph: "◐", name: "Retirement Planner", role: "Long-term readiness projections", accent: "text-gold" },
];

export default function Home() {
  return (
    <>
      <Head>
        <title>Alex — AI Portfolio Intelligence</title>
      </Head>
      <div className="min-h-screen app-bg text-ink">
        <header className="max-w-6xl mx-auto px-6 py-6 flex justify-between items-center">
          <span className="font-display text-2xl font-semibold tracking-tight">Alex</span>
          <div className="flex items-center gap-3">
            <SignedOut>
              <SignInButton mode="modal">
                <button type="button" className="btn btn-secondary text-sm">
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button type="button" className="btn btn-primary text-sm">
                  Get started
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link href="/dashboard">
                <button type="button" className="btn btn-primary text-sm">
                  Open app
                </button>
              </Link>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>
          </div>
        </header>

        <section className="max-w-6xl mx-auto px-6 pt-16 pb-24 text-center animate-fade-up">
          <p className="eyebrow mb-4">Multi-agent financial intelligence</p>
          <h1 className="font-display text-5xl sm:text-6xl md:text-7xl font-semibold leading-[1.05] tracking-tight max-w-4xl mx-auto">
            Your portfolio,
            <span className="text-gold"> interpreted</span> by a team of AI specialists
          </h1>
          <p className="text-muted text-lg sm:text-xl mt-8 max-w-2xl mx-auto leading-relaxed">
            Autonomous agents analyze holdings, visualize allocation, assess risk, and project
            retirement — orchestrated in parallel on enterprise infrastructure.
          </p>
          <div className="flex flex-wrap gap-4 justify-center mt-12">
            <SignedOut>
              <SignUpButton mode="modal">
                <button type="button" className="btn btn-primary px-8 py-3 text-base">
                  Start free analysis
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link href="/dashboard">
                <button type="button" className="btn btn-primary px-8 py-3 text-base">
                  Go to dashboard
                </button>
              </Link>
            </SignedIn>
            <Link href="/advisor-team">
              <button type="button" className="btn btn-secondary px-8 py-3 text-base">
                Meet the advisors
              </button>
            </Link>
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-6 py-20 border-t border-border">
          <p className="eyebrow text-center mb-10">The advisory team</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {AGENTS.map((agent) => (
              <div key={agent.name} className="panel p-6 hover:border-gold/30 transition-colors">
                <span className={`text-3xl font-display block mb-4 ${agent.accent}`} aria-hidden>{agent.glyph}</span>
                <h3 className={`font-display text-xl font-semibold ${agent.accent}`}>
                  {agent.name}
                </h3>
                <p className="text-muted text-sm mt-2 leading-relaxed">{agent.role}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-6 py-20">
          <div className="panel-raised p-10 md:p-14 text-center">
            <h2 className="font-display text-3xl font-semibold mb-4">
              Built for clarity, not noise
            </h2>
            <p className="text-muted max-w-xl mx-auto mb-8">
              Structured reports, interactive charts, and risk scoring — delivered when your agents
              finish their run.
            </p>
            <SignedOut>
              <SignUpButton mode="modal">
                <button type="button" className="btn btn-sage px-8 py-3">
                  Create your account
                </button>
              </SignUpButton>
            </SignedOut>
          </div>
        </section>

        <footer className="border-t border-border py-8 text-center text-xs text-muted px-6">
          <p>Alex · For informational purposes only · Not investment advice</p>
        </footer>
      </div>
    </>
  );
}
