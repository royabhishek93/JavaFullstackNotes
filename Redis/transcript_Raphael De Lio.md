0:08
radius and explore its capabilities and
0:11
limitations so let's get started
0:16
[Music]
Pub/Sub in a Nutshell
0:23
sub stands for publish And subscribe it
0:26
is a pattern in computer programming
0:27
that involves allowing message to be
0:29
sent from one component of an
0:31
application to one or many other
0:33
components without those components
0:35
being directly connected or having a
0:38
direct relationship with one another
0:41
think of it like a radio broadcaster the
0:44
publisher broadcasts audio and the
0:46
subscribers listen to the audio being
0:47
broadcast
0:49
the publisher does not need to know who
0:51
the subscribers are and the subscribers
0:53
they don't need to know who the
0:54
publisher is the only thing that matters
0:57
is the message being broadcast
1:00
in Pub sub components can send message
1:03
to a central topic or Channel and other
1:06
components can subscribe to the channel
1:08
to receive those messages
1:10
this allows for decoupled communication
1:13
between components and makes it easier
1:16
to manage the flow of information in a
1:18
complex system
Pub/Sub In Redis
1:20
web Sub in redis
1:23
redis implements the pub sub pattern by
1:26
providing a simple and efficient
1:27
messaging system between clients in
1:30
reality's clients can publish messages
1:32
to a named Channel and other clients can
1:34
subscribe to the channel to receive the
1:36
messages when a client publishes a
1:38
message to a channel red is delivers
1:40
that message to all clients that are
1:42
subscribed to the channel
1:44
this allows for real-time communication
1:46
and the exchange of information between
1:48
separate components of an application
1:51
redis Pub sub provides a lightweight
1:54
fast and scalable solution that can be
1:56
used for various use cases such as
1:59
implementing real-time notifications
2:01
sending messages between microservices
2:03
or communicating between different parts
2:05
of a single application synchronous
Synchronous Communication
2:08
communication
2:11
redis Pub sub is synchronous subscribers
2:15
and Publishers must be connected at the
2:17
same time in order for the message to be
2:19
delivered think of it as a radio station
2:21
you're able to listen to a radio while
2:24
you're tuned into it however you're
2:26
incapable of listening to any message
2:27
broadcasts while your radio was off red
2:30
is Pub sub we will only deliver the
2:32
message to Connected subscribers this
2:35
means that if one subscriber loses
2:37
connection and this connection is
2:39
restored later on it won't receive any
2:41
missed message or be notified about them
2:44
therefore it limits use cases to those
2:46
that can tolerate potential message loss
2:50
fire and forget
2:53
fire and forget is a messaging pattern
2:55
where the sender sends a message without
2:57
expecting an explicit acknowledgment
2:59
from the receiver that message was
3:01
received the sender simply sends the
3:04
message and moves on to the next task
3:06
regardless of whether the message was
3:08
actually received by the receiver or not
3:12
redis Pub sub is considered a fun forget
3:15
messaging system because it does not
3:16
provide an explicit acknowledgment
3:19
mechanism confirming that the message
3:21
was received by the receiver instead
3:23
messages are broadcast to all active
3:26
subscribers and it is the responsibility
3:28
of the subscribers to receive and
3:30
process those messages
3:33
fan out only reddit's Pub sub is found
Fan Out Only
3:36
out only meaning that
3:38
when the publisher sends a message it is
3:40
broadcast to all active subscribers all
3:44
subscribers receive a copy of the
3:46
message regardless of whether they are
3:47
specifically interested in the message
3:50
or not now that we've seen how red is
3:53
implements the pub sub functionality
3:55
let's put our hands in the fire and see
3:58
how it works in practice let's do it
Hands On
4:00
everybody let's put our hands in the
4:02
fire as you can see I already have my my
4:04
instance of the Reddit server running
4:05
locally in a Docker container if you
4:07
still don't have one if you still don't
4:08
have a redis instance where you can play
4:10
with don't forget to watch my video
4:12
where I show you how we can spin up
4:15
quickly and easily a Docker container
4:18
with the redis stack within it but
4:21
without further Ado let's continue what
4:23
we're going to be doing here is we're
4:24
going to open three different
4:25
connections with our ready server let me
4:28
open three different terminals here two
4:30
of them which are those in the left are
4:32
gonna act as the subscribers while the
4:34
one in the right is going to act as the
4:35
publisher right so
4:37
the first thing you're going to do is in
4:39
each one of them we're going to connect
4:40
to our ready server I'm going to be
4:43
doing it using the docker command Docker
4:45
exact that allows me to execute a
4:48
command within the container and this
4:49
command is going to be ready quickly
4:52
while the container is red is a stack
4:54
this is the name of my container I'm
4:56
running this command within my container
4:58
to connect within the redis command line
5:01
interface I'm going to be doing this
5:03
in all of them
5:05
okay all of them are now
5:07
connected good and what I'm going to be
5:10
doing here in this one is I'm going to
5:12
subscribe to multiple channels you'll
5:15
see that the Subscribe command can
5:16
receive multiple channels as the
5:18
arguments I'm going to be
5:20
subscribing to the crazy Channel and
5:23
also the code Channel
5:26
cool you can see that we received back
5:28
two different on event notifications
5:30
they are both of the same kind subscribe
5:35
this one subscribed to the crazy Channel
5:38
and this one subscribing to the code
5:39
Channel and the third element of this
5:42
event notification is the number of
5:44
channels that are subscribed by this
5:47
subscriber so you can see that for the
5:49
first one it was one and for the second
5:51
one it was true right while in our
5:53
second client what we're going to be
5:56
doing is using a different command which
5:58
is the Please Subscribe that instead of
6:00
receiving the Channel's name it receives
6:02
patterns right so in this case what
6:04
we're going to be doing is
6:07
subscribing to all channels whose name
6:10
ends with underscore Channel and also
6:12
all channels whose name and with
6:15
underscore chat
6:17
okay you can see that the same thing
6:19
happened but now we have a different
6:20
kind of event notification and also
6:23
patterns instead of actual Channel names
6:25
and now that we have both of our
6:27
subscribers subscribed to something
6:29
let's get to our publisher and publish
6:32
our first message so publish shoot the
6:35
crazy Channel
6:37
the message
6:39
this channel is hella crazy okay press
6:44
enter
6:45
and you can see that this message has
6:47
appeared in both of our subscribers
6:48
right away right this is a new event
6:51
notification this time it's saying that
6:54
we received a message
6:56
in the crazy Channel and the message was
6:58
this channel is hella crazy and the same
7:00
thing
7:01
here in our second subscriber right now
7:05
let's try to send a different message
7:07
but now to a channel that that is only
7:09
subscribed in one of our subscribers so
7:13
this time we're going to be sending a
7:15
message to Let's publish
7:17
ensure the dog's chat
7:20
woof woof this is going to be our
7:22
message
7:24
woof woof oops
7:29
okay and then we can see that the first
7:33
subscriber didn't receive anything
7:34
because it's not subscribed to the dog's
7:37
chat channel right while the second one
7:40
since it subscribe to all the channels
7:42
that has underscore chat as the suffix
7:46
of their name
7:48
it actually received the message so you
7:50
can see that you received the P message
7:53
um in the docs chat woof woof basically
7:55
okay another thing to bear in mind is
7:58
that you don't need to create channels
7:59
manually right you just need to
8:01
subscribe to a Channel or publish into a
8:03
channel and Reddit will do the rest for
8:05
you automatically you just need to worry
8:06
about publish or subscribing to channels
8:11
and all right that's basically it super
8:14
simple to get started you can see that
8:15
all you need is a ready server and a few
8:18
clients to connect to it and publish
8:21
messages and subscribe to messages super
8:23
easy to get started you can also do it
8:25
through the most popular programming
8:28
languages Java python you name it and
8:32
yes that's it let's jump to the
Conclusion
8:35
conclusions now Radice provides a simple
8:37
and Powerful solution for real-time
8:39
messaging systems through its Pub sub
8:41
functionality
8:43
it's lightweight easy to implement and
8:45
integrate into existing systems it can
8:48
also support a large number of
8:49
subscribers and handle High volumes of
8:51
messages with low latency
8:53
besides that messages are delivered in
8:56
the order that they are published
8:58
it is important to know that the use
8:59
cases are limited to those that can
9:01
tolerate message laws and that don't
9:03
require explicit acknowledgment of
9:04
messages by the receiver these
9:07
limitations should be considered when
9:08
determining the suitability of redis web
9:11
sub as a message broker for a particular
9:13
use case however these limitations can
9:16
be overcome when using red as the
9:18
strings the subject of our next video
9:21
stay tuned my name is Rafael De Liu if
9:24
you like this video please don't forget
9:25
to subscribe to the channel and hit the
9:27
like button down below see you around

All

From the series

From Coding with Raphael De Lio

APIs

Presentations

Learning


15:59


---

## Scenario-Based Questions

1. **A subscriber's connection drops for two minutes due to a network blip, and several messages are published to its channel during that gap.** What happens to those messages once the subscriber reconnects, and why?**
   They are lost. Redis Pub/Sub is synchronous and only delivers to subscribers connected at the moment of publishing; there is no buffering or replay for a subscriber that was offline, so reconnecting does not recover the missed messages.

2. **A publisher sends a message and immediately moves on without checking whether any subscriber actually processed it.** What messaging pattern does this describe, and what guarantee is explicitly absent?**
   Fire-and-forget. There is no acknowledgment mechanism confirming the message was received or processed by any subscriber; the publisher has no way to know delivery succeeded.

3. **You need one subscriber to react only to channels ending in `_chat` and another to react only to channels ending in `_channel`, without hardcoding every channel name.** Which command supports this, and how does it differ from `SUBSCRIBE`?**
   `PSUBSCRIBE` with a glob-style pattern (e.g., `*_chat`, `*_channel`). Unlike `SUBSCRIBE`, which matches exact channel names, `PSUBSCRIBE` matches any channel name fitting the pattern, so new channels created later are automatically covered.

4. **A message is published to a channel that currently has zero subscribers.** What happens to that message, and what does this imply for use cases that require guaranteed delivery?**
   The message is simply dropped; nothing stores it for a future subscriber. This makes Pub/Sub unsuitable for use cases where every message must eventually be processed, since a message published with no active listener is gone forever.

5. **You want to build a "user is typing…" indicator in a chat UI, where an occasional missed update is harmless.** Is Redis Pub/Sub a good fit here, and why?**
   Yes. The fire-and-forget, fan-out-only nature is acceptable because losing an occasional typing-indicator update does not break the user experience, and low latency matters more than guaranteed delivery.

6. **You want to build an order-processing pipeline where every order must be handled even if a worker was temporarily offline when it was published.** Is Redis Pub/Sub the right tool, and what should you use instead?**
   No. Pub/Sub cannot replay missed messages to a worker that was disconnected. A Redis Stream with consumer groups (or another durable queue) is more appropriate because it retains entries and lets a worker resume unprocessed work after reconnecting.

7. **A developer expects to have to explicitly "create" a channel before anyone can publish or subscribe to it, similar to creating a table.** Is that necessary in Redis Pub/Sub?**
   No. Channels are created implicitly the moment any client subscribes or publishes to a given name; there is no separate provisioning step, unlike heavier messaging systems that require explicit topic/channel creation.

8. **Two different subscriber types (say, a logging service and a notification service) both subscribe to the same channel, but only the notification service cares about a particular message published to it.** What does "fan-out only" mean for this scenario?**
   Both subscribers receive a copy of every message published to that channel, regardless of whether they are interested in it; Redis does not filter delivery based on subscriber-side interest, so the uninterested subscriber must discard irrelevant messages itself.

9. **Your system now needs guaranteed delivery, replay for a reconnecting consumer, and acknowledgment that a message was actually processed.** Which Redis feature should you migrate the messaging layer to, and what does it add that Pub/Sub lacks?**
   Redis Streams. They persist entries so consumers can replay missed data and provide consumer groups with an acknowledgment (PEL/`XACK`) mechanism, overcoming Pub/Sub's fire-and-forget, no-replay limitations.
