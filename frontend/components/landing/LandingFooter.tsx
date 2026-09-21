export default function LandingFooter() {
  return (
    <footer className="bg-surface-container-lowest pt-20 pb-10 border-t border-surface-variant">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
         <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-12">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary text-xl">air</span>
              </div>
              <span className="font-headline-sm text-on-surface font-bold tracking-tight">VayuNet</span>
            </div>
            <div className="text-body-sm text-on-surface-variant flex gap-6">
               <a href="#" className="hover:text-primary transition-colors">Documentation</a>
               <a href="#" className="hover:text-primary transition-colors">API Reference</a>
               <a href="#" className="hover:text-primary transition-colors">Science Methodology</a>
               <a href="#" className="hover:text-primary transition-colors">Privacy</a>
            </div>
         </div>
         <div className="text-center text-label-sm text-outline border-t border-surface-variant pt-8">
            &copy; {new Date().getFullYear()} VayuNet Federated Environmental Intelligence. All rights reserved.<br/>
            DEMONSTRATION DATA ONLY. Not for actual regulatory enforcement.
         </div>
      </div>
    </footer>
  );
}
