# How do you prevent a coupon code from ever being redeemed twice across multiple users?

**Type:** Advanced Scenario-Based
**Topic:** Redis Core Data Types — Sets
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Use a **Set** and treat "add the coupon code to the redeemed set" as the actual redemption check. `SADD redeemed-coupons COUPON123` returns `0` if the code is already a member (meaning: someone already redeemed it) and `1` if it was newly added (meaning: this redemption is the one that counts) — and that single atomic call *is* your race-condition-proof check.

## Easy Explanation
A Set never allows duplicates, and `SADD` tells you honestly whether your item was "new" or "already there." So instead of first checking "does this coupon exist?" and then separately adding it (two steps, with a gap a second request could sneak through), you just try to add it and trust the return value: `1` means you're the first and only winner, `0` means someone beat you to it, even if that happened a millisecond earlier.

## Diagram
```
Two users try to redeem the SAME coupon code at nearly the same instant:

User A                          Redis Set: redeemed-coupons                User B
  SADD redeemed-coupons "SAVE20" ------> not a member yet -> ADD -> returns 1
                                                                        SADD redeemed-coupons "SAVE20" -> already a member -> returns 0
  (1 = "you got it, proceed")                                    (0 = "too late, reject this redemption")
```

## Production Example
```java
Long result = redisTemplate.opsForSet().add("redeemed-coupons", "SAVE20");
if (result != null && result == 1) {
    applyDiscount(order);   // this call is the one true winner
} else {
    throw new CouponAlreadyRedeemedException();
}
```

This is safer than "check with `SISMEMBER`, then `SADD` if not found" as two separate calls, because two concurrent requests could both pass the `SISMEMBER` check before either one calls `SADD` — recreating the exact race condition a single atomic `SADD` avoids.

## Why Interviewers Ask This
It tests whether a candidate recognizes that Sets naturally solve "has this exact value ever been used" problems (coupon codes, idempotency tokens, deduplicating unique visitor IDs) and — critically — that the *single* `SADD` call itself must be the enforcement point, not a separate existence check beforehand.
