package com.moviebooking.model.enums;

public enum SeatType {
    REGULAR(1.0),
    PREMIUM(1.5),
    RECLINER(2.0),
    VIP(2.5);

    private final double priceMultiplier;

    SeatType(double priceMultiplier) {
        this.priceMultiplier = priceMultiplier;
    }

    public double getPriceMultiplier() {
        return priceMultiplier;
    }
}
