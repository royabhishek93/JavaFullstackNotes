0:00
Hello everyone.
0:01
Today I'm going to talk about a specific question around
0:05
the system design of WhatsApp.
0:08
So as we know that system design is not about reading a particular solution
0:14
and taking those solutions as a phase value, but rather they are generally
0:19
discussion between two or multiple.
0:22
Where a solution is thrown up on.
0:24
And then you try to see whether this solution actually maps
0:29
through the requirement or not.
0:31
So these discussions of system design can happen anywhere.
0:34
They can happen in an interview room.
0:38
They can happen in your workplace where you are pitching a solution.
0:42
You are saying that, Hey, let's use Redis, or let's use this
0:45
Kafka and build a solution.
0:48
So in such cases, Taking things as a face value from internet is not enough.
0:56
You need to scratch the surface.
0:58
You need to go one level beyond and see whether this solution is good for you
1:04
or not, or why this solution should be chosen compared to some other solution.
1:10
So one such question around this is whether one should use Redis or Kafka
1:17
in their chatting application, like.
1:21
Let's deep dive into it.
1:23
Before deep diving into the problem statement, let's first
1:27
see what Redis and Kafka are.
1:29
If you are already aware of this concept, then you can skip this section
Redis & Kafka Basics
1:34
and move to the next section, which I have mentioned in the timeline.
1:40
So let's see what Redis is.
1:45
So if you go to the Redis document, It is in memory database by in
1:52
memory database that it means that it keeps data in memory.
1:56
It doesn't keep in disk, it keeps in disk, but when it serves through
2:01
the data, it keeps in memory.
2:03
So it is very fast.
2:05
It was primarily used for caching.
2:09
The red is cash is something which you have heard, which
2:12
you would have heard a lot.
2:14
So it is used.
2:16
But there is one surprise, or for many of us that Redis is not just
2:23
used for caching, but it is used for many of the other purposes as well.
2:28
It is used for pub sub model that is published and subscriber.
2:31
It is used for transactions, so it is used for many other
2:36
places and not just for cash.
2:39
And coming to Kafka.
2:40
If you see Kafka, it's also quite popular technology, which is built by Apache,
2:47
but it is so popular that there are a lot of distributions of Kafka built by
2:53
Confluence and other parties as well.
2:56
So what is Kafka?
2:57
Kafka is a streaming service.
2:59
Streaming service.
3:00
It's a publisher subscriber model again, where.
3:05
You publish a data to a Kafka topic, that is you publish a data
3:10
and then you can consume a data.
3:12
So just like in Redis, you have a publisher subscriber
3:16
Redis solution available.
3:18
You have a publisher subscriber available in Kafka as well.
3:23
But there is this one difference between the two, which makes
3:27
them entirely different solution and if entirely different use
3:30
case is that red says in memory.
3:34
But Kafka is not.
3:35
Kafka writes messages in the desk.
3:39
So if you publish a message to a Reds, it will be pushed in memory,
3:47
possibly in the network buffer, and then pushed to the subscriber.
3:52
But in case of Apache Kafka, when you publish a message,
3:56
it gets written to the desk.
3:59
These operations are asynchronous.
4:01
So the ride happens on the disc, and then there are consumers
4:07
who could consume from the disc.
4:10
So the, the advantage of that is that the consumer, even if the consumer
4:16
is not live, consumer is dead and then they wake up one day, they can
4:20
consume all their messages, even if the messages were delivered sometime.
4:28
But that's not the case for Redis.
4:30
So Redis doesn't store any message.
4:32
They have pubs are modeled, but they don't store anything.
4:36
You send a message to Redis, the publisher sends a message to Redis, and it will
4:42
be in memory and it will never be stored in a desk, and the communication
4:47
will be as if it is over the wire from the publisher to the subscriber.
4:52
So it is very fast.
4:54
There is no disc operation.
4:57
It's all in memory.
4:58
Whereas in Kafka, it's stored and persisted in a disc.
5:03
So when it's persisted in a disc, you need to allocate some space for
5:08
all the topics which are created and using the disc operations.
5:14
These things are.
5:15
So these are the net net difference between the two, which which will
5:20
be the pivotal point of the design choices which you would make.
5:25
So I think now we are
5:26
clear with both Redis and Kafka, at
5:30
least the basics of it.
5:32
You can of course go
5:33
ahead and read about
5:35
them
5:35
and see what radius and Kafka are, but for the sake
5:40
of this particular
5:41
problem, state.
5:42
This much
5:43
should be enough.
5:44
Now let's move to the problem statement.
problem statement
5:46
The problem statement is simple, that you have Alice, you have Bob, and you
5:51
want them to chat with each other.
5:52
That the simple problem statement, you want to have a text based communication.
5:57
It can be a chatting application, but you can also have a gaming
6:01
application like chess as well with a similar problem state.
6:05
It must be a low
6:06
latency and messaging
6:08
will be frequent.
6:09
So Alice and Bob are the people who would keep on messaging each other.
6:13
So if you see here Alice sending message to Bob.
6:18
So one of the design choices is to have a backend and via
6:22
backend they can communicate
6:23
with each other.
6:25
And since the backend could horizontally scale, there would be multiple backends.
6:32
So they would need.
6:33
Database or they would need a storage where they could
6:37
publish and receive the message.
6:40
So that's the design choice we are taking.
6:42
So if there are multiple backends, they would publish a message and
6:46
they would consume a message.
6:48
Now, when we see publisher and consumer, we would want to know
6:53
whether to use Redis or Kafka.
6:56
So
6:56
let me just expand this problem statement
6:59
a little more.
7:06
So this is
7:07
the exact solution
Traditional solution
7:09
which you would find online in a lot of places, that in such case you
7:15
will have multiple backend machines.
7:18
So this
7:18
layer can scale itself
7:21
horizontally.
7:22
And this red is also horizontally scalable.
7:25
So, and of course the
7:27
users are you know,
7:29
they can scale as much as they want.
7:32
So there would be
7:32
Alice, Bob, and Eve, and
7:35
other people would be chatting with each other.
7:38
So there would
7:39
be a lot of users.
7:41
These
7:42
backend services can horizontally scale and you can use Redis as a solution.
7:48
So this is a typical solution available for a chatting application.
7:52
And what you do is whenever two people communicate with each
7:56
other, you publish the message to
7:59
a.
7:59
One.
7:59
So Bob is connected
8:03
to backend Machine one, and Alice is connected to backend machine two,
8:07
if they're connected to the same
8:08
machine.
8:08
You don't even need Redis or
8:11
anything because that machine can do a lot of in memory operations.
8:15
But these layer also has to be horizontally scale.
8:20
So Bob will send a message to back in one, and then back from back in one.
8:25
The message will be published to.
8:28
And then from Reds, the message will be published to Backend two.
8:34
In fact, backend two will be subscribing to that same channel,
8:39
and then Alice will get the message.
8:41
So you see there is one connection between backend to front end, and
8:46
there are two connections from Redis.
8:50
So one is for publishing and the other is striving.
8:53
So yes, you need to have two
8:55
connections to Redis, to, to the consumer
8:59
and subscriber stuff.
9:01
Not the natural question, which you might stumble upon in any discussion
9:07
room is why do you want to use Redis for publisher subscriber?
9:12
It's counterintuitive.
9:14
Most of the cases is
9:15
something using kaf.
9:19
Many places you would've seen or many, it's quite popular to use
9:23
Kafka as a streaming service.
9:25
Why on earth we want to use Redis?
9:27
So this is the exact question we will try to answer.
9:30
So for that, what I have done is I
9:32
have made set up on
9:34
my local for both Redis and Kafka so that I can explain a few of the differences
9:41
by running the code so that once you run the code, you can see by example that.
9:47
This is the exact difference which we can observe between the Kafka,
9:52
although bits and pieces we have already discussed, but let's just see
9:56
the exact difference around the both.
9:59
So let me first share the setup, which I have done for Kafka.
Demo and explanation
10:04
So I have started my zookeeper.
10:08
So when you run Kafka, you need to do two things.
10:11
You need to start a zookeeper and then you need to start.
10:14
And then you need to create a topic on which you would be publishing
10:18
and subscribing the message.
10:21
So here, if you see I have started my zookeeper, I have
10:25
started my Kafka as well.
10:27
You can find a tutorial online.
10:29
It's straightforward to download and run the Kafka.
10:33
I'm not going to waste your time on this.
10:36
And then what I have done is
10:37
that I have created a.
10:41
So it's a simple command to create a topic, a Kafka topic, create.
10:46
And I have already done that.
10:47
So the setup of Kafka is done.
10:49
You create a topic, you are now ready to publish and subscribe to the message.
10:56
So this stuff is done.
10:58
And
10:58
then I have started a
11:00
producer in the consumer in Kafka.
11:02
So you
11:03
can see that you know, I have started a,
11:07
a consumer.
11:08
If
11:09
you see here Kafka console,
11:11
this is the
11:12
producer and this is the consumer.
11:15
So both the things are ready and they both are ready to
11:19
publish message to each other.
11:21
So the first thing
11:21
first is that you know creating
11:25
a topic, whenever you
11:26
create a topic lot of messages
11:30
do get
11:30
populated.
11:31
So if I just run just hold
11:36
on, clear.
11:40
If I
11:40
run this and let's say
11:43
I create a topic one, anything.
11:48
So you would say it's a heavy operation and you would see a lot of
11:52
logs getting populated whenever new topic
11:57
is created.
11:58
So it's, it's a heavy
12:01
operation.
12:01
It's not as
12:02
simple as, You know, just calling the api there
12:06
is a lot of backend operations,
12:08
which are done.
12:10
So.
12:11
And now let's move on to the chatting part, or producer and consumer part.
12:17
So let's say this producer wants to send a message.
12:19
Hello.
12:23
You could observe, I'm, I'm sure you would be able to observe.
12:26
There is some delay in the time, at the time when the message is sent
12:31
and at the time when the message is.
12:36
Okay, so you can see the publisher and subscriber model of the Kafka.
12:42
And similarly we can
12:44
move to the reds.
12:46
So
12:46
I have set up reds on my machine
12:48
as well.
12:49
You can install
12:50
reds.
12:51
It's quite straightforward.
12:52
You can go online and see how to install reds on local
12:54
and again, not going to waste
12:56
your time setting up
12:58
the reds.
12:58
So I have started my Reds server and then.
13:02
This is what I have
13:03
done.
13:04
I have subscribed
13:06
to a channel here.
13:09
The one interesting thing is that you don't even need to create a
13:12
channel to subscribe to a channel.
13:14
You can subscribe to any channel you want to.
13:16
It won't exist anywhere.
13:18
It just a channel and all the operations will happen in memory.
13:21
So I have to a channel one, and if I publish a message,
13:26
It instantaneously comes here.
13:29
So you see message, it's a message of type message on channel one
13:34
because I have subscribed to channel one, I could subscribe to multiple
13:37
channels and the message is, hello.
13:40
If I again type something
13:45
like, how are you, you.
13:51
The message is instantaneous.
13:54
It's very fast.
13:55
And this is how the publisher and subscriber model of
13:58
the red is, is working.
14:00
I am able to publish to a channel and the message goes to the
14:04
channel and the subscriber
14:05
is able to see the message instantaneously.
14:08
Why instantaneously?
14:09
Because red is all in memory.
14:12
Whereas in Kafka, it was not all in memory, it was going to a.
14:17
And then from the disc it was reading and then giving you the data.
14:21
So NetNet, you can see both the publishing subscriber model
14:25
in Reds as well as in Kafka.
14:27
So
14:28
now we can go ahead and compare the differences between Redis
14:34
and Kafka in terms of chatting
14:37
application.
14:38
So the first thing, first, we
14:41
can see that the credit
14:44
is the right.
14:46
In our problem statement here, and the main reason for this,
14:51
so there are four reasons.
14:53
The first reason around this is that red is faster than kaka.
14:57
So you want to have a faster application.
15:01
You want to have an application where the chatting happens very fast.
15:05
You don't want the disc operations to happen.
15:08
So Redis is faster.
15:10
So if I publish any message from the publisher,
15:25
It is instantaneous.
15:26
Whereas if I go to Kafka, Kafka, publisher and subscriber,
15:42
It does take some time to reflect, so it's less faster
15:47
compared to Redis, and
15:49
we want the communication to be faster.
15:53
And we can't do that in case of Kafka.
15:56
Of course there would be some, at times it would be acceptable
16:00
to have a delay of one second
16:01
or so.
16:02
But the operations
16:04
are always is in chronus that is publishing to a, a file and then
16:10
reading from the file or disc.
16:12
So that's the
16:13
first thing where the,
16:15
the problem
16:16
arises.
16:17
And the second
16:19
is, Cost of
16:23
creating and cost of creating
16:27
a topic.
16:28
So
16:29
if you see here when
16:31
I was
16:32
creating topic in Kafka, or
16:36
I can create one more such topics here.
16:39
Let's say I create a topic too.
16:42
It
16:42
does do some disc corporations.
16:45
You see that, you know, it's trying to create some space and
16:49
some parti some, some
16:51
space in the partitions and Kafka would have multiple
16:54
partitions.
16:54
So you know,
16:56
the, the creating of Kafka topic is not a trivial thing, which
17:00
you would do here and there.
17:02
That is, it is not going to happen that person when Alice wants to talk
17:06
to Bob.
17:07
So creating
17:09
a Kafka topic is something which would be needed, which would be done because
17:14
at times those operations can be heavy.
17:16
These are the persistence layer where these things would happen.
17:20
So, of.
17:22
Instead of doing things in memory, you are now allocating a space in the Kafka
17:27
cluster in different
17:29
Kafka machines.
17:31
So there will be multiple machines in the Kafka cluster as well, and
17:34
you would need to propagate that
17:36
message that topic is
17:38
created and at times it can take some time.
17:40
Also, it's not going to be instantaneous just
17:42
like this just like
17:43
the local machine.
17:45
So it'll take some time for the Kafka message or, or the
17:48
Kafka topic to be created.
17:51
So of
17:52
course it's not something
17:53
which you would want.
17:55
Whereas if I move to Redis, you see here, if, let's say I pause
18:01
it and I pause both producer and consumer, let me just clean it
18:10
and now I want to
18:18
see like I will.
18:21
Connect to red is on my local.
18:25
And then let's say I subscribe
18:31
to any channel, any channel, any channel I want.
18:41
So I have subscribed to this channel, any channel.
18:45
This is
18:45
the first thing which
18:47
gets printed, which means that you have subscribed to any.
18:50
Here I can publish through any channel.
19:06
I don't even need to create a a channel.
19:10
I can just send a message and it's all in memory and it's even faster.
19:14
So there is no space requirement.
19:17
These two are entirely different problem statements.
19:20
One is the Kafka, which is all around the storage part, where the
19:26
moment you create a Kafka, you would need to deal with the partitions.
19:30
You would need to.
19:32
Internally it will char,
19:35
it will take the concept of charting that it will distribute the data into
19:39
different partitions
19:41
within the cluster.
19:42
So a lot of heavier operations would
19:44
be done.
19:45
It won't be just simple command
19:49
being run.
19:50
It will do a lot of things in the background, but whereas here, you
19:53
don't even need to create a channel.
19:56
So the storage requirement, that's the second part.
19:58
There is no third part.
20:00
In fact, there is no storage requirement.
20:02
In case of red is you don't need to store the message.
20:06
Whereas in Kafka, you would need to store the message.
20:09
You can set the retention policy by default.
20:12
Generally, there are seven days for
20:14
Kafka, but Kafka's also
20:17
different problem and red is also different problem.
20:19
So for chatting application, again, Redis is a good.
20:23
So
20:23
the first is around the
20:26
storage.
20:27
The first is around the speed.
20:30
The second is around the storage, and the third is around the cost
20:35
of creating the Kafka topic.
20:37
So you can see that the cost of creating a Kafka topic is much more than the cost of
20:42
creating the ka guard.
20:44
There is no
20:46
such cost
20:46
in case of Now the last
20:50
point, let me move to the last point here.
20:54
So we have already talked about the faster communication already, no
20:58
storage and creating a Kafka topic, the last it cost of deleting a topic.
21:04
So what if Alice and Bob, they were chatting and then they said, Hey,
21:08
goodnight and we'll talk tomorrow.
21:10
So would you want the space to be allocated for Alice and.
21:16
Kafta the Kafka topic, you would want to delete it and next day when they come
21:21
live, they, you would want to connect them again because it's a real time chat.
21:25
So in case of Kafka post of deleting a topic is more, in fact,
21:31
let me just share a couple of articles, which I went to and I
21:37
found that the deleting
21:39
of Kafka topic is not straight.
21:42
It is something which might require some work as well.
21:46
So there, there is this command to delete a Kafka topic, you can just
21:50
run this command and you can delete.
21:52
But even before doing that, you need to enable the dilution of the Kafka
21:57
topic.
21:58
So specifically
21:59
you have to go to a Kafka property and enable the relation of the topic, and
22:03
then you will need to run this command to.
22:07
Also, it would happen that at times the deletion wouldn't
22:10
happen, or it'll take some time.
22:12
It'll be an asynchronous operation and it'll take some
22:15
time to get the topic deleted.
22:17
But even if it doesn't happen, in case the topic deletion doesn't
22:23
happen, then you have to go manually and you have to manually delete the.
22:29
the, the topic by logging into the server and eventually you might also
22:34
have to restart the Kafka server.
22:36
So here in the,
22:36
the accepted documentation,
22:39
if you.
22:40
Accepted struggle.
22:42
So answer, that's what they mentioned, that you have to specifically stop the
22:46
Kafka server and then get rid of topic.
22:49
So you see that there is a lot of inertia or there is a lot of hindrance
22:54
in creating a topic and deleting a topic.
22:56
And yeah, it is straightforward,
22:58
but it is asynchronous
23:01
and it will require some effort to be.
23:05
And that is something which you would not want to do all the time, that,
23:09
hey, let's create a topic when Allison wants, Bob wants to talk and let's
23:13
delete it when they don't want to talk.
23:15
So in such cases, having the red solution is much, much, much better.
23:21
So if you just see the red, I can just
23:24
publish to any any channel
23:29
I
23:29
want to, and I can publish
23:32
to channel one.
23:34
Since there is no subscriber of
23:36
Channel one you don't
23:38
get any message.
23:39
But now if you subscribe to channel one, so you wouldn't get the previous message
23:45
as well, that facility was there in Kafka.
23:48
That is in Kafka.
23:50
The consumers can start and they can read the message even before they were created.
23:56
But in case of Redis, they are just.
23:59
So Reds is all about the performance.
24:02
Reds does not take into the consideration of the storage of
24:05
message.
24:06
And and yeah,
24:08
it solves all together a different problem.
24:10
So if, now again, if I publish a message, you would see the
24:16
reds accepting the message.
24:18
So up.
24:20
Now if we, if you see the
24:22
system design diagram,
24:24
which we were talking about earlier, so.
24:27
You can publish a message to a Reds channel, and if there is a third person
24:31
like Eve, and that person Connect is connected to one of the backend machines,
24:36
so you can create one more channel.
24:40
And by creating a channel, I mean that you don't even need to create a channel.
24:44
They would just be
24:45
connected by, you know,
24:47
Bob sending a message to some
24:48
channel and other consumer
24:51
would receive to, let's say, channel two.
24:56
That's how the
24:56
design of reds is and that's how
25:00
the design choices can be made here.
25:02
Now there is one more question which people can ask that, Hey, I
25:06
want to store my messages as well.
25:08
That is, if Ellis and Bob, Bob wake up in the morning, they should be
25:12
able to see what chat they did.
25:15
A day before yesterday.
25:16
So that's a different problem statement.
25:18
It cannot be clubbed with the communication problem statement
25:21
that has storage problem.
25:22
And for the storage problem, there are multiple solutions.
25:25
One is storing at the server end.
25:27
And for that you can have a Kafka consumer or Redis consumer, and that
25:33
consumer can put the data
25:35
into their database or you can even store the message in their own
25:39
machine just like WhatsApp does, and then sync that message to Google.
25:44
Or iCloud.
25:45
So that's a storage problem, and that should be solved separately.
25:48
If you try to mix two different problem statement, then a lot of confusion arises.
25:54
So that's all for this video.
Conclusion
25:56
I hope.
25:56
I was able to clarify when to use Redis and specifically why to use
26:01
Redis in a chatting application.
26:03
At times it it's important
26:06
for us to scribe the service and come up with the reasons because in system design
26:11
it'll happen that you throw a solution.
26:14
the people, the people are going to ask you
26:17
why you have given a particular solution.
26:20
Why not something
26:22
else you read online in that, hey, use Redis for a chatting application.
26:26
They would ask you, why not Kafka or why not a no equal database?
26:31
So having a proper justification will help you to be more convinced.
26:36
And of course you should try
26:37
out these greatest and Kafka and
26:41
then experiment and figure out as.
26:44
I will also share some of the commands and you can run those commands on your
26:49
machine to see how they're performing.
26:52
That's all from my side for this video.
26:54
I hope you like it.
26:55
If you like it, please like and comment.
26:57
It really makes a difference.
26:59
Till the next week, bye.

All

From the series

From Better Dev with Anubhav

APIs

Computer programming

Presentations


---

## Scenario-Based Questions

1. **You are designing a real-time chat feature with horizontally scaled backend instances, where Alice and Bob may be connected to different backend nodes.** Why is a shared publish/subscribe layer needed at all instead of just handling messages in-process?**
   When two users are connected to different backend instances, one instance has no direct way to reach the other's client. A shared broker lets one instance publish a message and the other subscribe to receive it, bridging communication across independently scaled instances.

2. **For the same low-latency chat requirement, why would Redis typically respond faster than Kafka when a message is published?**
   Redis operates entirely in memory, so publishing and delivering a message avoids any disk I/O. Kafka persists messages to disk as part of its write path, and reading a message back involves disk access, which is inherently slower.

3. **Your team is tempted to create a distinct Kafka topic for every new chat conversation.** Why is this heavier than simply having two users subscribe to a Redis channel, and what operational cost does it introduce?**
   Creating a Kafka topic involves allocating partitions and propagating that creation across the broker cluster, which is a non-trivial, sometimes slow operation, unlike a Redis channel, which requires no explicit creation step. Doing this per conversation adds real overhead at scale.

4. **Two users finish chatting and go offline for the night.** Why is deleting the corresponding Kafka topic more troublesome than simply having zero subscribers on a Redis channel, and what does this mean for a chat feature with constant conversation churn?**
   Deleting a Kafka topic is not immediate; it may require enabling topic deletion in configuration, running an explicit delete command, waiting for an asynchronous completion, and sometimes manual server-side intervention. A Redis channel needs no deletion at all — it simply has no subscribers when nobody is listening, making it far cheaper for frequently starting/ending conversations.

5. **Users expect to open the app the next morning and see yesterday's conversation history.** Is that something Redis Pub/Sub (or Kafka's consumer replay) should be responsible for, and what is the correct way to handle it?**
   No — that is a separate storage/persistence problem, not a real-time delivery problem. The recommended approach is to have a consumer (or the backend) write messages to a database (or sync to cloud storage) as they arrive, and serve chat history from that persistent store rather than from the messaging layer itself.

6. **Despite Redis being faster for this specific chat scenario, in what kind of system would Kafka be the better choice over Redis?**
   When you need durable, disk-backed retention with configurable retention periods, consumers that can join and read historical messages even after being offline, and very high-throughput event streaming across many independent consumers — none of which fits Redis Pub/Sub's fire-and-forget, in-memory-only model.

7. **A message is published to a Redis channel that currently has no subscriber connected.** What happens to it, and why does this matter for a chat application's reliability expectations?**
   The message is simply dropped, since Redis Pub/Sub does not store messages for later delivery. This means the chat's real-time layer alone cannot guarantee delivery to an offline recipient — a separate persistence mechanism is required to make sure the message is not truly lost.

8. **A junior engineer proposes solving "real-time delivery" and "storing chat history" with the exact same Redis Pub/Sub mechanism.** Why does mixing these two problem statements lead to confusion, and how should they be separated?**
   Real-time delivery (getting a message to an online recipient instantly) and durable storage (retrieving history later, even after being offline) are different problems with different guarantees. They should be designed and solved independently — Pub/Sub (or Streams) for live delivery, and a database or persistent store for history — rather than forcing one mechanism to satisfy both requirements.
