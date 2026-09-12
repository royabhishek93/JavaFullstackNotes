# Push vs Pull Notification Delivery — APNs vs FCM — LinkedIn Post

## Post Text (copy-paste ready)

Your server never talks to a phone directly — and if 5 notifications arrive while you're offline, Apple only saves the LAST one.

- Phones sit behind carrier NAT, change IPs constantly, and sleep — direct delivery is physically impossible
- APNs and FCM maintain a persistent connection to every device on the planet; your backend just hands them the payload
- Registration flow: app requests token from OS → iOS/Android generates device token → app sends it to your backend → stored in a device_tokens table
- Offline behavior differs: APNs stores only the LAST notification per topic ("last wins"), while FCM queues up to 100 messages with a 4-week default expiration
- A 410 Gone response means the token is dead — delete it from your DB immediately, or APNs rate-limits you for spamming invalid tokens
- WhatsApp-style chat uses silent "background" pushes to wake the app, which then fetches messages over its own socket — message content never touches Apple's/Google's servers

Swipe → to see the full APNs registration flow, offline storage internals, and the token cleanup lifecycle.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Your server can't reach a phone directly. APNs/FCM relay it — and APNs only keeps the LAST offline notification. Here's the full flow. 📲

### Variant B — Long (400–600 chars)
"Just send a push notification" hides a surprisingly deep system: phones are behind carrier NAT and sleep, so Apple/Google run persistent connections to every device and relay on your behalf. APNs uses HTTP/2 multiplexing (600K notifications/sec per app on one pooled connection) and a "last wins" offline cache, while FCM queues up to 100 messages for 4 weeks. Miss the 410 Gone cleanup step and your token table rots with millions of dead entries. Full breakdown inside — save it for your next system design round.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM local time (peak engineering audience scroll window before standups).

## Engagement Hook
Ask in the comments: "Have you ever debugged a 'missing notification' bug that turned out to be APNs 'last wins' silently dropping 4 of 5 pushes? What happened?"
