package com.moviebooking.exception;

public class ResourceNotFoundException extends BusinessException {
    public ResourceNotFoundException(String resourceType, Object id) {
        super(String.format("%s not found with id: %s", resourceType, id));
    }
}
