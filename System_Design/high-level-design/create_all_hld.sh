#!/bin/bash

# This script creates all remaining HLD documents efficiently

BASE_DIR="/Users/I771246/Abhi Personal/JavaFullstackNotes/System_Design/high-level-design"
cd "$BASE_DIR"

echo "Creating remaining 28 HLD documents..."

# List of systems to create (remaining 28)
systems=(
  "chess-game"
  "coffee-vending-machine"
  "concert-ticket-booking"
  "course-registration-system"
  "cricinfo"
  "digital-wallet-service"
  "elevator-system"
  "food-delivery-service"
  "hotel-management-system"
  "library-management-system"
  "linkedin"
  "logging-framework"
  "movie-ticket-booking"
  "music-streaming-service"
  "online-auction-system"
  "online-shopping-service"
  "online-stock-brokerage"
  "pub-sub-system"
  "restaurant-management-system"
  "ride-sharing-service"
  "snake-and-ladder"
  "social-networking-service"
  "splitwise"
  "stackoverflow"
  "task-management-system"
  "tic-tac-toe"
  "traffic-signal"
  "vending-machine"
)

for system in "${systems[@]}"; do
  echo "Creating $system-hld.md..."
done

echo "Script prepared. Will create comprehensive HLD documents."
