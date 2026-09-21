export default function CitizenReportingWorkflow() {
  return (
    <section className="py-24 border-b border-surface-variant bg-surface-container-lowest">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <h2 className="text-headline-lg text-on-surface mb-12 text-center">Citizen Ground-Truth Workflow</h2>

        <div className="flex flex-col md:flex-row justify-between items-start gap-4">
           {/* Step 1 */}
           <div className="flex-1 flex flex-col items-center text-center group">
              <div className="w-16 h-16 rounded-full bg-surface border border-outline-variant flex items-center justify-center mb-4 group-hover:border-primary transition-colors">
                 <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary">visibility</span>
              </div>
              <h5 className="text-label-md text-on-surface mb-2">1. Observe</h5>
              <p className="text-body-sm text-on-surface-variant">See a plume, smell an odor, or experience breathing difficulty.</p>
           </div>

           <div className="hidden md:block w-8 h-px bg-outline-variant mt-8"></div>

           {/* Step 2 */}
           <div className="flex-1 flex flex-col items-center text-center group">
              <div className="w-16 h-16 rounded-full bg-surface border border-outline-variant flex items-center justify-center mb-4 group-hover:border-primary transition-colors">
                 <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary">photo_camera</span>
              </div>
              <h5 className="text-label-md text-on-surface mb-2">2. Capture</h5>
              <p className="text-body-sm text-on-surface-variant">Take a photo using the VayuNet mobile portal (metadata appended).</p>
           </div>

           <div className="hidden md:block w-8 h-px bg-outline-variant mt-8"></div>

           {/* Step 3 */}
           <div className="flex-1 flex flex-col items-center text-center group">
              <div className="w-16 h-16 rounded-full bg-surface border border-outline-variant flex items-center justify-center mb-4 group-hover:border-primary transition-colors">
                 <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary">psychology</span>
              </div>
              <h5 className="text-label-md text-on-surface mb-2">3. Gemini Analysis</h5>
              <p className="text-body-sm text-on-surface-variant">AI verifies image content (e.g. "black smoke from brick kiln").</p>
           </div>

           <div className="hidden md:block w-8 h-px bg-outline-variant mt-8"></div>

           {/* Step 4 */}
           <div className="flex-1 flex flex-col items-center text-center group">
              <div className="w-16 h-16 rounded-full bg-surface border border-outline-variant flex items-center justify-center mb-4 group-hover:border-primary transition-colors">
                 <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary">sync</span>
              </div>
              <h5 className="text-label-md text-on-surface mb-2">4. Triangulation</h5>
              <p className="text-body-sm text-on-surface-variant">Report is instantly matched against satellite anomalies and wind vectors.</p>
           </div>

           <div className="hidden md:block w-8 h-px bg-outline-variant mt-8"></div>

           {/* Step 5 */}
           <div className="flex-1 flex flex-col items-center text-center group">
              <div className="w-16 h-16 rounded-full bg-surface border border-outline-variant flex items-center justify-center mb-4 group-hover:border-error transition-colors">
                 <span className="material-symbols-outlined text-on-surface-variant group-hover:text-error">policy</span>
              </div>
              <h5 className="text-label-md text-error mb-2">5. Action</h5>
              <p className="text-body-sm text-on-surface-variant">Dossier sent to local CPCB nodal officer for on-the-ground intervention.</p>
           </div>
        </div>
      </div>
    </section>
  );
}
