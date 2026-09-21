import LandingHeader from '@/components/landing/LandingHeader';
import HeroSection from '@/components/landing/HeroSection';
import LiveStatusStrip from '@/components/landing/LiveStatusStrip';
import InteractiveMap from '@/components/landing/InteractiveMap';
import AnomalyCatalog from '@/components/landing/AnomalyCatalog';
import SignatureConcept from '@/components/landing/SignatureConcept';
import FusionArchitecture from '@/components/landing/FusionArchitecture';
import LifecycleTimeline from '@/components/landing/LifecycleTimeline';
import EventExplorer from '@/components/landing/EventExplorer';
import Perspectives from '@/components/landing/Perspectives';
import CitizenReportingWorkflow from '@/components/landing/CitizenReportingWorkflow';
import Methodology from '@/components/landing/Methodology';
import LandingFooter from '@/components/landing/LandingFooter';

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-on-background selection:bg-primary/30 selection:text-primary-fixed overflow-x-hidden font-body-md">
      <LandingHeader />

      <main>
        <HeroSection />
        <LiveStatusStrip />
        <InteractiveMap />
        <AnomalyCatalog />
        <SignatureConcept />
        <FusionArchitecture />
        <LifecycleTimeline />
        <EventExplorer />
        <Perspectives />
        <CitizenReportingWorkflow />
        <Methodology />
      </main>

      <LandingFooter />
    </div>
  );
}
