export interface Trip {
  id: string;
  userId: string;
  destination: string;
  startsOn: string;
  endsOn: string;
  budgetMinor: number;
}

export function formatTripSummary(trip: Trip): string {
  return `${trip.destination}: ${trip.startsOn} to ${trip.endsOn}`;
}

export function estimateDailyBudget(trip: Trip): number {
  const days = Math.max(1, Date.parse(trip.endsOn) - Date.parse(trip.startsOn));
  return Math.ceil(trip.budgetMinor / days);
}
