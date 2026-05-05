import { Booking, calculateSpend, summarizeBooking } from "../services/bookings";

export async function bookingSpendRoute(userId: string): Promise<string> {
  const booking: Booking = {
    id: "booking-demo",
    userId,
    hotelMinor: 188000,
    transportMinor: 42000,
    foodMinor: 28000,
  };
  return summarizeBooking(booking);
}

export async function bookingSpendValue(userId: string): Promise<number> {
  const label = await bookingSpendRoute(userId);
  return calculateSpend({
    id: label,
    userId,
    hotelMinor: 188000,
    transportMinor: 42000,
    foodMinor: 28000,
  });
}
