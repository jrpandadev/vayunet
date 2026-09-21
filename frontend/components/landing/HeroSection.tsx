export default function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden border-b border-surface-variant">
      {/* Decorative Grid Background */}
      <div className="absolute inset-0 z-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, var(--color-on-surface) 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>

      {/* Glow Effect */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/20 blur-[120px] rounded-full z-0 pointer-events-none"></div>

      <div className="container relative z-10 mx-auto px-gutter-mobile md:px-gutter text-center max-w-4xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/10 mb-8">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          <span className="text-label-sm text-primary uppercase tracking-widest">Federated Intelligence Pipeline</span>
        </div>

        <h1 className="text-display-xl-mobile md:text-display-xl text-on-surface mb-6 leading-tight">
          Pollution is an <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">Event</span>,<br className="hidden md:block" /> Not Just a Number.
        </h1>

        <p className="text-body-lg text-on-surface-variant mb-10 max-w-2xl mx-auto">
          We fuse citizen ground-truth, authoritative sensor data, and Sentinel-5P satellite telemetry to detect, verify, and resolve hyper-local environmental anomalies.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-space-md">
          <a href="#explorer" className="w-full sm:w-auto h-12 px-8 rounded-full bg-on-surface text-surface text-body-md font-bold flex items-center justify-center gap-2 hover:bg-surface-variant hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-lg">explore</span>
            Explore Anomalies
          </a>
          <a href="#concept" className="w-full sm:w-auto h-12 px-8 rounded-full border border-outline-variant text-on-surface text-body-md font-bold flex items-center justify-center gap-2 hover:border-primary hover:text-primary transition-colors">
            <span className="material-symbols-outlined text-lg">account_tree</span>
            View Architecture
          </a>
        </div>
      </div>
    </section>
  );
}
