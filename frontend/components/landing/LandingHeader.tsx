import Link from 'next/link';

export default function LandingHeader() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-surface-variant bg-background/80 backdrop-blur-md">
      <div className="container mx-auto px-gutter-mobile md:px-gutter h-16 flex items-center justify-between">
        {/* LOGO */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
            <span className="material-symbols-outlined text-on-primary text-xl">air</span>
          </div>
          <span className="font-headline-sm text-on-surface font-bold tracking-tight">VayuNet</span>
        </div>

        {/* NAV */}
        <nav className="hidden md:flex items-center gap-space-lg">
          <a href="#concept" className="text-body-sm text-on-surface-variant hover:text-primary transition-colors">Concept</a>
          <a href="#fusion" className="text-body-sm text-on-surface-variant hover:text-primary transition-colors">Fusion</a>
          <a href="#explorer" className="text-body-sm text-on-surface-variant hover:text-primary transition-colors">Explorer</a>
          <a href="#methodology" className="text-body-sm text-on-surface-variant hover:text-primary transition-colors">Methodology</a>
        </nav>

        {/* CTA */}
        <div className="flex items-center gap-space-sm">
          <Link href="/signin" className="hidden md:flex items-center justify-center h-10 px-4 rounded-full text-body-sm font-medium text-on-surface hover:bg-surface-variant transition-colors">
            User Portal
          </Link>
          <Link href="/dashboard" className="flex items-center justify-center h-10 px-4 rounded-full bg-primary text-on-primary text-body-sm font-semibold hover:bg-primary-fixed-dim transition-colors shadow-[0_0_15px_rgba(78,222,163,0.3)]">
            Authority Console
          </Link>
        </div>
      </div>
    </header>
  );
}
