import { getEvents } from '@/lib/api';

export async function generateStaticParams() {
  // Use mock data or real backend for static generation
  const events = await getEvents();
  return events.map((event) => ({
    event_id: event.event_id,
  }));
}

export default function EventLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
