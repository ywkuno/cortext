import { formatTripSummary, Trip } from "../services/trips";

export async function listTrips(userId: string): Promise<Trip[]> {
  return [
    {
      id: "tabi-demo",
      userId,
      destination: "Kyoto",
      startsOn: "2026-06-10",
      endsOn: "2026-06-18",
      budgetMinor: 280000,
    },
  ];
}

export async function tripSummary(userId: string): Promise<string> {
  const trips = await listTrips(userId);
  return formatTripSummary(trips[0]);
}
