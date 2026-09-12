# Push vs Pull Notification Delivery
### APNs (Apple) vs FCM (Google) — What Happens When Phone Is Offline

---

## PART 1 — THE STUDENT CONVERSATION

**When your server wants to notify a user's phone, it can't just open a connection to the phone. The phone is behind a carrier's firewall, it changes IP addresses constantly, and it's often sleeping.**

Apple and Google solve this with a central relay. Instead of your server connecting directly to each phone, it connects to Apple's Push Notification Service (APNs) or Google's Firebase Cloud Messaging (FCM). These services maintain persistent connections to every iOS and Android device in the world and relay your notifications.

**Your server → APNs/FCM → device**

The device maintains a long-lived TCP connection to APNs/FCM (called the "push channel"). This connection is established by the operating system itself, not your app. It works even when your app is closed, because the OS manages it.

---

## PART 2 — HOW APNs (APPLE PUSH NOTIFICATIONS) WORKS

```
Registration (one-time per device):
────────────────────────────────────────────────────────────────────

  User installs your app → iOS asks: "Allow notifications?"
  User taps Allow.

  iOS:
  1. Generates a device token (unique to this app + device combination)
     Token = SHA256(device_id + app_bundle_id + cert)  ← ~32 bytes
  2. Sends token to your app via APNs registration callback

  Your app:
  3. Sends token to your backend: POST /devices { token: "abc123...", userId: 42 }

  Your backend:
  4. Stores: device_tokens table { user_id: 42, token: "abc123...", platform: "ios" }

Push notification send:
────────────────────────────────────────────────────────────────────

  Your Backend → APNs:
  HTTP/2 POST https://api.push.apple.com/3/device/{device_token}
  Headers:
    apns-topic: com.yourapp.bundleId
    apns-push-type: alert
    apns-priority: 10      ← immediate (vs 5 = conserve power)
    apns-expiration: 1704153600   ← discard if not delivered by this time
    authorization: Bearer {JWT signed with your APNs key}
  Body:
  {
    "aps": {
      "alert": { "title": "New Message", "body": "Alice: Hello!" },
      "badge": 3,
      "sound": "default"
    },
    "custom_data": { "chat_id": "chat_123" }
  }

  APNs → iOS device (via persistent push channel):
    Delivers notification.
    iOS displays it. User sees it.

  APNs response to your backend:
    200 OK → delivered to APNs (not necessarily to device yet)
    410 Gone → device token is invalid (user uninstalled app) → delete token from DB
    429 Too Many Requests → back off with exponential backoff
```

---

## PART 3 — WHAT HAPPENS WHEN PHONE IS OFFLINE

```
Offline delivery:
────────────────────────────────────────────────────────────────────

  User Alice turns on airplane mode at 9:00 AM.
  Your server sends 5 notifications to Alice throughout the day.

  Each notification is sent to APNs:
  APNs stores the LAST notification per topic (not all 5).
  "Last wins" — APNs overwrites previous undelivered notifications.

  At 5:00 PM: Alice turns off airplane mode. iPhone reconnects to APNs.
  APNs delivers the stored notification (the last one sent).
  Alice receives 1 notification (not 5).

  apns-expiration header controls storage duration:
  If expiration=0 → APNs delivers immediately or discards (no storage)
  If expiration=timestamp → APNs stores until that time, then discards

  For critical notifications (new message):
    Set expiration = now + 24 hours
    → Alice will get it when she comes back online within 24 hours

  For time-sensitive notifications (flash sale ends in 1 hour):
    Set expiration = sale_end_time
    → If Alice doesn't come online before sale ends → APNs discards

FCM behavior is similar:
  Stores up to 100 messages per device (not just the last one)
  Default expiration: 4 weeks
  collapse_key: optional key to overwrite pending notifications (like APNs last-wins)
```

---

## PART 4 — DEVICE TOKEN MANAGEMENT

```
Token lifecycle and the 410 problem:
────────────────────────────────────────────────────────────────────

  Token invalid when:
  → User uninstalls the app
  → User restores phone from backup (new token issued)
  → Token expires (APNs rotates tokens periodically)

  Your backend sends notification → APNs returns 410 Gone:
  {
    "reason": "Unregistered",
    "timestamp": 1704067200
  }

  What you must do:
  DELETE FROM device_tokens WHERE token = "abc123..." AND last_updated < 1704067200
  (timestamp check: if user reinstalled and got same token back, don't delete)

  If you don't clean up stale tokens:
  → Your DB accumulates millions of invalid tokens
  → APNs rate limits you for sending to invalid tokens
  → You waste resources sending to uninstalled apps

  Token rotation (iOS 13+):
  Apple now issues rotating device tokens for privacy.
  The app gets a new token periodically even without reinstalling.
  Your app should re-register the token on every app launch.
  Use didRegisterForRemoteNotificationsWithDeviceToken callback.
```

---

## PART 5 — DIRECT PUSH (FOR CHAT — DATA NOTIFICATIONS)

```
Two types of APNs notifications:
────────────────────────────────────────────────────────────────────

  1. Alert notification (visible notification):
     iOS displays banner, sound, badge.
     User must be reachable.
     "apns-push-type": "alert"

  2. Background/data notification (silent notification):
     iOS wakes your app silently in the background.
     App fetches new data, updates local state.
     User sees nothing immediately (no banner).
     "apns-push-type": "background"
     "content-available": 1

  WhatsApp-style chat:
  Use DATA notification to wake the app, app fetches new messages via WebSocket.
  Then app shows LOCAL notification (OS-level, no network required).
  Why? More reliable: data notification + local display vs sending full content via APNs.
  Security: message content never passes through Apple's servers.
```

---

## PART 6 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your notification system needs to send push notifications to iOS and Android. How does the architecture work?"

**You (architect answer):**

> "Sending directly to phones isn't possible — devices are behind carrier NAT, change IPs,
> and sleep. Apple and Google each maintain a persistent connection to every device globally.
> You deliver through APNs for iOS and FCM for Android.
>
> The device registration flow: on first launch, the app requests a push token from the OS.
> iOS calls APNs, gets a device token, returns it to our app. The app sends this token to
> our backend: POST /devices with the token, user ID, and platform. We store it in a
> device_tokens table.
>
> When we need to push: our Notification Service calls APNs HTTP/2 API with the device
> token as the URL path, a JWT signed with our APNs key as auth, and the notification
> payload as JSON body. APNs relays it to the device.
>
> Key design decisions: I use HTTP/2 multiplexing — APNs supports it, so one TCP
> connection to APNs can carry thousands of simultaneous push requests. I use a
> connection pool of 10 HTTP/2 connections to APNs, recycled every hour.
>
> For offline delivery: I set apns-expiration to 24 hours for chat messages.
> If the device comes online within 24 hours, APNs delivers it. For time-sensitive
> promos (1-hour flash sale), I set expiration to the sale end time.
>
> The critical operational task is token hygiene: when APNs returns 410 Gone, I
> delete the token from the DB. Without this, you accumulate millions of stale tokens
> and APNs rate-limits you."

---

## QUICK REFERENCE CARD

```
APNs (iOS):
  Auth: JWT signed with APNs auth key (or certificate-based)
  Protocol: HTTP/2 (multiplexed, connection reuse)
  Offline storage: last notification per topic stored until expiration
  Token invalid: 410 Gone → delete from DB

FCM (Android):
  Auth: Service account key or project API key
  Protocol: HTTP/1.1 (legacy) or HTTP/2 (v1 API)
  Offline storage: up to 100 messages, 4-week default expiration
  collapse_key: overwrite pending notifications (like APNs last-wins)
  Token invalid: error "registration-token-not-registered" → delete from DB

Device token lifecycle:
  Created: first app launch, user grants permission
  Changes: OS update, app reinstall, token rotation (iOS 13+)
  Invalidated: uninstall, token expired, app disabled notifications
  Best practice: re-register token on every app launch

Notification types:
  Alert:      visible notification (banner, sound, badge)
  Background: silent wake-up, app fetches data, shows local notification
  Use background for chat (content stays off Apple/Google servers)

Scale consideration:
  HTTP/2 multiplexing: 1 connection → thousands of concurrent pushes
  Connection pool: 10 HTTP/2 connections to APNs per notification pod
  APNs rate limit: 600K notifications/second per app (very generous)

Interview one-liner:
"Phones can't be reached directly — they're behind carrier NAT and sleep.
APNs and FCM maintain persistent connections to every device. Your server
pushes to APNs, APNs relays to device. Tokens are per-device-per-app,
must be kept fresh (410 Gone = delete the token)."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** "How do you actually get a notification to a phone?" is asked in almost every notification system design — APNs/FCM is the only real answer.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **03 — Notification System** | This is the entire delivery mechanism. Phones can't be reached directly — APNs (iOS) and FCM (Android) maintain persistent connections to every device globally. Your notification worker calls APNs/FCM HTTP/2 API with device token + payload. APNs stores the last notification for offline devices until expiration. 410 Gone response = delete the invalid token from DB. |

**Architect's one-liner for the interview:**
*"Your server never talks to a phone directly — it hands the payload to APNs or FCM and they deliver it over the persistent connection they maintain with every device."*
