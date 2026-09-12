# Push vs Pull Notification Delivery — APNs (Apple) vs FCM (Google) — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 23 of 29

## HOOK (0:00–0:30)

[Screen cue: split screen — your backend server on the left, a phone on the right, with a big red "X" over a direct line drawn between them]

Quick question. Your backend just processed an order. You want to tell the customer's phone "your order shipped" — right now, this second. So... you just open a connection to their phone and send it, right?

Wrong. You *can't*. Your server cannot just open a connection to a phone. The phone is sitting behind its carrier's NAT, its IP address changes every time it hops between WiFi and cellular, and half the time the screen is off and the radio is asleep to save battery.

So how does WhatsApp get a message to your lock screen in under a second? How does Swiggy tell you "your order is out for delivery" the instant it happens? There's a relay in the middle — one that Apple and Google run for you — and today we're going inside it.

[Screen cue: title card — "Push vs Pull: APNs vs FCM"]

## THE PROBLEM (0:30–2:00)

[Screen cue: diagram — server trying to reach phone directly, blocked by "Carrier NAT" wall]

Let's be precise about why direct push is impossible. Three reasons.

One — carrier NAT. Your phone doesn't have a stable public IP. It's behind layers of network address translation on the mobile carrier's side. There's no fixed address for your server to dial into.

Two — IP churn. The phone switches between WiFi networks, cellular towers, airplane mode. Its address changes constantly. Even if you captured an IP five minutes ago, it's stale now.

Three — sleep. iOS and Android aggressively suspend background processes and radios to save battery. Your app isn't even running most of the time. There's no process on the phone listening for your server's connection attempt.

[Screen cue: text overlay — "The only thing awake 24/7 is the OS push channel"]

So Apple and Google solved this at the operating system level, not the app level. Every iOS device maintains one single persistent, encrypted TCP connection back to Apple's servers — the Apple Push Notification service, APNs. Every Android device does the same thing with Firebase Cloud Messaging, FCM. This connection is owned by the OS, not your app. It survives your app being closed, force-quit, even deleted from the recent-apps list. It's one of the few things guaranteed to be alive.

So the real architecture is never "server talks to phone." It's always: **your server → APNs or FCM → the phone's OS-level push channel → your app.** You're handing your notification to a relay that Apple or Google already built and already keeps warm for you. Let's build that flow end to end.

## THE SOLUTION (2:00–5:00)

[Screen cue: numbered flow diagram — "Registration" then "Send"]

There are two flows here. Registration happens once. Sending happens every time you want to notify someone.

**Registration flow, step by step.** User installs your app, iOS asks "Allow notifications?", user taps Allow. Now iOS generates a **device token** — think of it as a unique mailing address for this specific app on this specific device. It's roughly 32 bytes, derived from the device identity, your app's bundle ID, and Apple's signing cert. iOS hands that token to your app through a registration callback. Your app's job now is simple: ship that token to your own backend — `POST /devices` with the token and the user ID. Your backend stores it in a `device_tokens` table: user ID, token, platform. That's it. Registration done. You now have a mailing address for this device.

[Screen cue: code block — the HTTP/2 POST to APNs with headers highlighted]

**Send flow.** When your backend wants to push, it makes an HTTP/2 POST to `https://api.push.apple.com/3/device/{device_token}`. Four headers matter a lot here. `apns-topic` — your app's bundle ID, so Apple knows which app this belongs to. `apns-push-type` — is this a visible `alert` or a silent `background` wake-up, we'll get to that distinction in the deep dive. `apns-priority` — 10 means "delivered immediately," 5 means "conserve battery, deliver when convenient." And `apns-expiration` — a Unix timestamp telling Apple how long to hold onto this notification if the device is offline right now.

Authentication is a JWT, signed with your APNs private key, sent as a bearer token — no long-lived session, no cookie, just a signed token per connection. And the body is JSON: an `aps` object containing `alert` — title and body text, `badge` — the little red count number, and `sound`. You can attach your own custom data alongside it for the app to use once it wakes up.

[Screen cue: three response codes stacked — 200, 410, 429 — with color coding: green, red, yellow]

Then APNs responds. **200 OK** means "I've accepted it and I'm relaying it" — note, that's not the same as "the phone has it yet." **410 Gone** means this device token is dead — usually because the user uninstalled your app — and your job right now is to delete that token from your database. **429 Too Many Requests** means back off, you're sending too fast, apply exponential backoff before retrying.

That's the whole mechanical flow. Registration gets you an address. Sending is an HTTP/2 call with the right headers and a signed JWT. Simple on paper. The interesting part — the part that actually gets asked in interviews — is what happens when that phone is offline when you send.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: timeline — 9 AM airplane mode ON, five notification icons queuing up, 5 PM airplane mode OFF, only ONE notification appears]

Here's the scenario that trips people up in interviews every time. Alice turns on airplane mode at 9 AM. Over the course of the day, your server sends her five separate push notifications — five different chat messages, say. At 5 PM she turns airplane mode off and her phone reconnects to APNs.

How many notifications does she see? If you said five, that's the wrong answer — and it's the answer most engineers give on their first attempt.

The actual answer is **one**. APNs does not queue all five. It stores the *last* notification sent per topic and silently overwrites the earlier ones — this is often called "last wins" behavior. So Alice gets exactly one notification: whichever was sent most recently. The other four are gone, discarded, never delivered.

[Screen cue: text overlay — "apns-expiration is the dial that controls this"]

Now — what controls how long APNs is even willing to hold that last notification? That `apns-expiration` header from before. If you set it to zero, APNs tries to deliver immediately and discards it if the device isn't reachable — no storage at all. If you set a future timestamp, APNs holds the notification until that time, then discards it if still undelivered.

This is a real design decision, not a technical footnote. For a chat message, you'd set expiration to now plus 24 hours — if Alice comes back online within a day, she gets the notification. But for a flash sale that ends in one hour, you set expiration to the sale's end time — because a notification saying "sale ends in 10 minutes" that arrives three hours later, after the sale is over, is actively harmful. You want APNs to just drop it.

[Screen cue: comparison table — APNs vs FCM storage behavior]

FCM, interestingly, behaves differently — and this is a great thing to bring up if you're asked to compare the two. FCM stores up to **100 messages** per device, not just one. Default expiration is **four weeks**, far more generous than APNs. And FCM gives you a `collapse_key` — an opt-in mechanism where you explicitly say "these messages should collapse into just the latest one," giving you APNs-style last-wins behavior only when you ask for it. So FCM defaults to storing more, and lets you opt into collapsing; APNs defaults to collapsing per topic, and you control storage duration via expiration.

[Screen cue: red banner — "410 Gone — the token cleanup trap"]

Now the second trap: device token lifecycle. Tokens go invalid constantly — user uninstalls the app, user restores from a backup and gets a new token, or the token just rotates. When you send to a dead token, APNs replies **410 Gone** with a reason like "Unregistered." If you don't act on that — if you keep retrying the same dead token — two things happen. Your database silently fills up with millions of tokens that will never receive anything. And APNs starts **rate-limiting your app** for repeatedly hammering invalid tokens. So the moment you see 410, you delete that token, full stop. One subtlety: check the timestamp APNs gives you against your token's last-updated time — if the user reinstalled and got the *same* token back after you'd already marked it dead, don't nuke a token that's valid again.

There's also **token rotation on iOS 13 and later** — Apple now rotates tokens periodically for privacy reasons, even without a reinstall. The fix is simple but easy to forget: re-register the token on every single app launch using the `didRegisterForRemoteNotificationsWithDeviceToken` callback, don't assume a token you stored six months ago is still good.

[Screen cue: WhatsApp-style chat notification flow diagram — "data notification wakes app" → "app fetches over WebSocket" → "local notification shown"]

Last trap, and this is the one senior interviewers love: there are actually **two kinds of APNs notifications**. An **alert** notification is visible — banner, sound, badge — and its content sits inside the payload you sent to Apple's servers. A **background** notification, also called silent, has `content-available: 1` and no visible banner at all — it just wakes your app quietly so it can do work.

Here's why WhatsApp doesn't just send your chat message as an alert payload: **security**. If they put "Alice: hey, are you free tonight?" directly in the APNs alert payload, that plaintext message content would pass through Apple's servers. Instead, WhatsApp sends a silent *data* notification — just "you have a new message," no content — which wakes the app, the app pulls the actual encrypted message over its own WebSocket connection, decrypts it locally, and *then* shows a **local** notification generated entirely on-device. No message content ever touches Apple's infrastructure. That's the pattern to know: data notification plus local notification, whenever content privacy matters.

## REAL WORLD (8:00–9:30)

[Screen cue: interview room mockup — interviewer and candidate silhouettes]

Let's put this in an interview room. Interviewer says: "design the push notification piece of your system." A strong answer sounds like this: "Devices can't be reached directly — carrier NAT, IP churn, sleep — so I go through APNs for iOS and FCM for Android. On registration, the app gets a device token from the OS and reports it to my backend, which stores it in a device_tokens table. On send, my notification service calls APNs over HTTP/2 with a JWT signed by my APNs key, plus headers for topic, priority, and expiration."

Then the good candidates go one level deeper on performance: "APNs supports HTTP/2 multiplexing, so a single TCP connection can carry thousands of simultaneous push requests concurrently — I don't open a new connection per notification. I maintain a small connection pool, something like 10 HTTP/2 connections to APNs, and recycle them roughly every hour to avoid stale connection issues." And on scale: "APNs' documented rate limit is around 600,000 notifications per second per app — which is enormous, so for the vast majority of products, you'll hit your own backend's throughput limits long before you hit Apple's."

[Screen cue: logos — WhatsApp, Swiggy, Zomato, Paytm, PhonePe]

This exact pattern is running under products you use every day. WhatsApp's message notifications are the textbook data-notification-plus-local-notification pattern we just covered — content privacy by design. Swiggy and Zomato's "your order is out for delivery" and "rider has arrived" pings are alert-type pushes, usually with a fairly short expiration since a stale delivery update is actively confusing. And Paytm and PhonePe's transaction alerts — "₹500 debited" — are a case where you'd lean toward higher priority and shorter expiration too, because a transaction alert that arrives hours late has basically failed at its job. Same underlying APNs/FCM machinery, three very different expiration and priority strategies depending on what the notification is actually for.

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: recap bullets on screen — "No direct connection. OS-level relay. Last-wins offline. 410 = delete the token."]

So — recap. Your server never talks to a phone directly. It hands the payload to APNs or FCM, which maintain the one connection guaranteed to stay alive. Offline devices don't queue every notification — they get the last one, governed by your expiration header. And token hygiene, cleaning up on 410 Gone, is the operational discipline that keeps your whole system from grinding down over time.

[Screen cue: next episode title card — "024: MVCC — How PostgreSQL Reads Never Block Writes"]

Next episode, we're going from phones to databases — episode 24, MVCC, how PostgreSQL lets a read and a write happen on the same row at the same time without either one blocking the other. If you've ever wondered how a database serves a consistent snapshot while a transaction is mid-write right next to it, that's exactly what we're breaking down. See you there.
