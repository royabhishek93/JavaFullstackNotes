# High-Level Design: Airline Management System

## System Overview
Design a scalable airline management system handling flight bookings, check-ins, seat assignments, crew management, and real-time flight tracking across multiple airlines serving millions of passengers globally.

---

## Requirements

### Functional Requirements
1. **Flight Search**: Search flights by route, date, airline, class
2. **Booking Management**: Book, modify, cancel reservations
3. **Seat Selection**: View seat map, select/change seats
4. **Check-in**: Online check-in 24 hours before departure
5. **Payment Processing**: Multiple payment methods, refunds
6. **Passenger Management**: Profiles, frequent flyer programs
7. **Crew Management**: Pilot/crew scheduling and assignments
8. **Flight Operations**: Real-time status updates, delays, cancellations

### Non-Functional Requirements
1. **Scalability**: 10M+ bookings/month, 1000+ flights/day
2. **Availability**: 99.99% uptime
3. **Consistency**: Strong consistency for seat bookings
4. **Latency**: Search < 200ms, Booking < 2s

---

## Capacity Estimation

### Traffic
- Monthly Active Users: 5M passengers
- Daily Bookings: 300K/day = 3.5/sec (peak: 10/sec)
- Flight Searches: 10M/day = 115/sec

### Storage (5 years): ~1.2TB
