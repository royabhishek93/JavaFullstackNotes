package com.moviebooking.exception;

public class SeatNotAvailableException extends BusinessException {
    public SeatNotAvailableException(String message) {
        super(message);
    }
}
