export interface Booking {
  id: string;
  userId: string;
  hotelMinor: number;
  transportMinor: number;
  foodMinor: number;
}

export function calculateSpend(booking: Booking): number {
  return booking.hotelMinor + booking.transportMinor + booking.foodMinor;
}

export function summarizeBooking(booking: Booking): string {
  const total = calculateSpend(booking);
  return `${booking.id}: ${total}`;
}
