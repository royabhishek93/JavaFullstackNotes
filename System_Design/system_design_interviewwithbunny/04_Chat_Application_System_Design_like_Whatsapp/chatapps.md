0:00
[Music] Hello guys and welcome back to my
0:06
channel interview with Bunny and we are back with another video on system designing and the application that we
0:12
will be designing today is a chat server like WhatsApp or Facebook Messenger where the core functionality will be
0:18
users should be able to send and receive text message as well as the media file from the friends via direct or from the
0:25
group chat. So this will be the core functionality of this system. So since you guys are already familiar with how
0:32
the WhatsApp or the messenger service actually works. So I would not waste much time on explaining the system
0:38
rather I will jump to the main functionality or the main non-functional requirement that we have to solve over
0:43
here. So as I have said in all my previous video, system designing is quite a vague interview round where the
0:50
interviewer will give you a open-ended question like design WhatsApp and it is your responsibility completely to
0:58
interact with your interviewer and gather all the functional and the non-functional requirement for the
1:03
system. So without wasting much time, let's see what can be the functional and the non-functional requirement that we
1:09
have to keep in mind for designing this system. So the first requirement that we have to solve over here is user should
1:15
be able to sign up into our application. So as you already know once we install the WhatsApp application in our mobile
1:22
we have to first login with the help of our phone numbers. Hence our first requirement would be we have to give the
1:28
provision for the user for signing in and signing up into our application. Number two we have to support the
1:35
onetoone message. Number three, apart from onetoone messaging, we also have to
1:40
support some additional thing and that is the group messaging. So that will be our third requirement of the system.
1:47
Number four, user should be able to see all the message history on a particular chat. Number five, apart from just
1:53
sending the textual message, we have to give the provision to the user so that he can also send and receive media files
2:00
such as images and videos. So these are primarily the five requirements that we
2:06
will be solving over here in this video and apart from that we have to give some additional features such as whether the
2:13
message has been sent to our server whether it is successfully delivered to the person and number three the read
2:19
receipt of a particular message. So these are the core five to six functionality or the functional
2:24
requirement that we will be solving over here in this video. So let's first list down all these functionalities over
Gathering Functional/NonFunctional Requirement
2:31
here. Now let's see what will be the non-functional requirement that we have to solve or keep in mind while designing
2:38
a chat application such as WhatsApp. So let's list down all the non-functional requirement over here. So as I have said
2:44
in all my previous video, the first non-functional requirement that you have to gather from your interviewer is the
2:52
scale of the system. So let's see what can be the scale of this WhatsApp application. So here your interviewer
2:58
will tell that the total number of user for which we will be designing this system is around 1 billion. So here the
3:05
total number of user will be 1 billion. And let's estimate that a particular user on average send 100 message per
3:13
day. So the total message will be 100 message per day which turns out that the
3:19
total number of messages that we are supporting on a particular day is 100
3:24
billion messages per day. So I hope this is clear that this is the total scale of
3:29
the system. So for which we are developing this application and you can easily identify that this scale is quite
3:37
huge because supporting 100 billion message per day is really critical. So
3:42
if I just assume or just do a rough calculation over here that the total average size of the message including
3:48
the textual form as well as the video is around 1 KB then the total number of
3:53
messages that are getting saved in our back end is around 1 KB multiplied by
3:58
100 billion which comes out around 1 TV per day. So this is the total volume of
4:05
the messages both in the form of the textual as well as in the media file
4:10
that we have to save over here. So here you can easily make an estimation that how critical it is and how efficiently
4:17
we should design our system so that we can support this tremendous volume of information. So this will be the first
4:24
requirement or the first non-functional requirement and that is the scale of the system. Number two, what we have to
4:31
discuss? We have to discuss the cap theorem and as you know cap theorem tells that whenever you are creating a
4:37
distributed system you have to either compromise between the availability or within the consistency of the system. So
4:44
either your application or the module will be highly consistent or it will be highly available. You cannot achieve
4:50
both of them together. And here if you understand our system correctly our system here should be highly available
4:57
means there should be a zero or negligible downtime. So that the user can use our application at any moment of
5:04
the time but it should be a eventual consistent system means since this is not a bank related application so here
5:11
we can afford a eventual consistent system rather than a high consistent system. So it is clear that based on the
5:18
cap theorem here we should give the priority to the availability of the system much more than that of the
5:25
consistency. So here we will be focusing on the availability rather than the consistency of the system. Now the next
5:31
non-functional requirement is our system should have a very very low latency
5:36
because since this is a chat service the user will expect that the chat will be delivered to the receiver in a
5:43
negligible time frame. So here the next non-functional requirement will be low latency and as I always tell you
5:49
whenever you are discussing a non-functional requirement during your system designing always try to quantify
5:55
it. So here what we are targeting that our message should get delivered from the sender to the receiver in around 300
6:03
millisecond. So this is the maximum latency we should expect in our system. So that was the third non-functional
6:10
requirement of the system. Number four, our system should be highly reliable. Means whenever we are sending a text to
6:16
a friend or family, we will expect that there will be zero message lost in the system. Means once we send a message to
6:24
our friends or family that should get delivered to the receiver with zero message loss. So here the fourth
6:30
requirement is our system should be highly reliable. So these are primarily all the non-functional requirement that
6:37
we have to keep in mind while designing our system. So I hope you are clear with that what are the functional and the
6:44
non-functional requirement that we are trying to solve in this problem. So here you can see we are done with the first
6:50
step of our designing and that is the requirement gathering for all the functional and the non-functional
6:55
requirement. Now keeping in mind all these requirements. Now let's start with the second step of our designing and
7:02
that is identification of the core entity. So here if you look carefully in all our function requirement you can
7:08
easily identify that what can be the major core entity of our system. So here
7:14
the first core entity will be the users. Number two here we have to support the
7:19
group messaging. So the next core entity will be the group and number three the most important and that is the message
7:25
that we have to deliver to the user. So let's list down all the core entities. So since we are done with the two major
Entity Creation
7:32
step and that is gathering of the function and the non-functional requirement and number two identification of the code entry. Let's
7:39
now jump into the third step of our system designing and that is the API creation. And as I always tell you API
7:46
designing is very easy if you have collected all the functional requirement correctly. So let's see what will be the
7:52
major rest API endpoints that we need to fulfill all the functional requirement
7:57
of the system. So let's move to the third step of our system designing and that is the API design. So the first
API Creation
8:04
rest endpoint that we have to give over here or we have to provision over here is we have to support the functionality
8:11
of signing and sign up. So here we will be having two URL one for the sign up
8:16
and another for the signing. So let's list down these two endpoints over here and as you know while we are registering
8:22
into our system means we are submitting a data into our system. So this will be a post call. So the first endpoint will
8:29
be a register endpoint and it will be a postcon. So this is how the signature of the endpoint will look like. So here you
8:36
can see this will be our first endpoint and that is for registering a user into our application. And here in the post
8:43
body we have to submit the user metadata such as the name of the user, the email
8:48
id, phone number and all these things. So here if you are designing a WhatsApp then here you have to send the phone
8:54
number as a parameter otherwise if you are creating the messenger application then there you have to submit the email
9:01
id as a post body. So based on the system designing question that whatever you are designing mention it
9:07
accordingly. So this will be the first endpoint of our system. Now apart from this there will be few more endpoints
9:13
for onboarding a particular user means there will be some added functioning like updating the user metadata,
9:19
deleting a user metadata and so on. So here I'm just not mentioning all those things since I have already covered all
9:26
those things in my previous video. So here also you can keep all those things same. Now let's move to the next
9:31
endpoint for fulfilling the next functional requirement and that is sending the onetoone messaging within
9:38
our system. So let's see how it will look like. So here you can see this is how the signature of onetoone messaging
9:45
will look like. So here if you look carefully I have not mentioned a post or a get over here rather I have mentioned
9:51
a WS and what it stand for? WS stand for web socket. So here in any chat
9:58
application whenever you are having a conversation between two or multiple friends here the way we send the text
10:05
message or the videos in near real time is with the help of the web socket and
10:10
why we do not use an plain HTTP call that we will discuss it later that why
10:15
it is not advisable to send or receive a text with the help of a HTTP call rather
10:21
why we are using a web socket for doing a conversation. So I will explain those
10:26
thing in detail while we will be doing our highle design. So let's move to the next requirement or the next API
10:32
endpoint that we have to design to send the onetoone messaging and that is the chat history. So whenever a user will
10:40
try to see all the previous chat. So we have to give a provision to the user to see all those list of chat that he had
10:47
done in the past. So for that we will be having one more API endpoint and that is to see all the chat history and since
10:54
here we are retrieving data from our server. So this will be a get endpoint.
11:00
So let's see how it will look like. So this is how the endpoint will look like. So here you can see in the signature we
11:06
are sending the user ID as one of the parameter and in return we are sending the list of chat that we have for this
11:13
user ID. So it is like once we log into our WhatsApp application we can see all the list of chats that we have done in
11:20
the past and once we click on a particular chat or a particular group thereafter we can see all the list of
11:26
messages within that chat or within that group. So here this first endpoint will list down all the chats that you have
11:34
done in the past. I hope this is clear. Now the next endpoint will be once the user clicks on a particular chat we have
11:41
to show all the text messages that are there for a onetoone messaging. So the
11:46
third endpoint will look something like this. So here you can see this is how it will look like. And here also this will
11:52
be also in the form of the pagionation. But remember this pagination will be a
11:57
bit different. It is not a page nation that you normally show in a web view because there you can see we have to
12:04
click on 1 2 3 to go from one page to another. Rather here it will be in the
12:09
form of the lazy load. Means once the user scrolls up all the text messages on a particular page then we have to send
12:16
the next offset and thereafter we will get the next frame or the next block of the text messages in the reply. So here
12:23
remember this will be a lazy load rather than a normal pagination that we do for
12:28
a web page. So I hope we are clear with what are the API endpoints that we need
12:34
to implement onetoone chat messaging functionality. So I hope this is clear
12:39
but here if you look carefully I have not created any other endpoint to support the functionality like to
12:45
receive the delivery and the sent receipt of a particular message. This whenever you see that a message has been
12:51
sent you get a single tick. After that once it gets delivered it gets double tick and once the receiver reads that
12:58
message it gets a blue tick. So here to implement those functionality we are not
13:03
exposing any rest endpoint over here because all those things will be done
13:08
with the help of the web socket that we will be opening between the two user for the conversation. So I'm not mentioning
13:15
it over here. Now let's move to the next endpoint and that is to support the messaging functionality for the group
13:22
message and the first and the foremost thing that we have to do is we have to give the provision to the user to create
13:28
a group add members to the group and all these things. So let's see what are the major endpoints that we need over here
13:35
to create and manage a particular group. So let me list down all those endpoints over here. So to manage and create a
13:42
particular group here these are the list of endpoint that more or less you need. So here the first one is to create a
13:48
particular group then we have to add member in that group and then we have to give the provision to remove a user from
13:54
that group. So these are more or less the major endpoints that we need for the group management. Now since we have
14:01
created all the groups in our application. Now let's see what are the endpoints that we have to give to the
14:07
user to do a conversation within the group and similarly over here also to do a conversation within the group we have
14:14
to open a web soocket. So here also we will mention the same thing and that is we need a web soocket for doing the
14:21
conversation and number two we have to give the provision for the user to see the message history. So here there will
14:28
be one more endpoint to see all the messages on a particular group chat. So let me list down the signature of that
14:35
endpoint over here. So this is how it will look like. So here you can see we are sending the group ID in our API
14:41
endpoint and we are trying to find out all the list of the messages that are present in the group and this will also
14:47
come in the form of the pagionation or in the form of the lazy load. So these are the two endpoints that we need to do
14:53
a conversation within the group. So here if you can see we are almost done with all the major endpoints that we need to
15:01
implement all this functionality and as I've already told you I have not expose any endpoint to fulfill this requirement
15:09
like delivery receipt and the read receipt and number two for sending the textual and the media file because both
15:15
of them will be done with the help of the web socket and this we will explain in detail when we will be doing our
15:22
highle and the low-level designing of this system. So I hope we are done with the three step of our designing and that
15:29
is first one gathering of the functional and the non-functional requirement number two identification of the core
15:35
entity and number three the creation of the rest endpoint that are required to fulfill all the major functional
15:41
requirement. Now let's go to the next step of our system designing and that is the highle designing. So the highle
High Level Design
15:48
designing of this system is also quite simple and straightforward because in the highle designing we only try to
15:54
fulfill the functional requirement that we have discussed over here. So let's see what were the components that we
16:00
need to design our system. So the first and the foremost thing that we need is the user. So here we will be designing
16:07
some of the users which are nothing but some of the applications that are installed in our phone. So these are
16:12
some of the clients for us and obviously since here if you have seen we are supporting a scale of 1 billion and
16:19
obviously to support this amount of huge traffic we obviously need a load
16:25
balancer and API gateway to manage our traffic. So here we will introduce our
16:30
next component and that is a load balancer and a API gateway and the
16:35
primary role of this load balancer and the API gateway will be authentication and authorization rate limiting and
16:42
distributing the traffic uniformly across all our backend server and for that we will be using the roundrobing
16:49
approach. So let me mention all those functionalities or responsibilities over here. Now if you see the first
16:55
requirement that we have to fulfill over here is the user should be able to sign in and register into our application. So
17:02
here we will be having our first service called as the user service and the main responsibility of the user service will
17:09
be onboarding the user into our application. So here we will be having our first service called the user
17:15
service and since here we have to save the information of the user into our application. So here we need a database
17:23
called as the user database. So here we will be having our database here called
17:28
as the user DB. I hope this is quite clear and straightforward because this is the same design pattern that we have
17:34
followed in our last seven videos. So here our traffic is coming into our load
17:40
balancer and here the user service will persist all the information in the user
17:45
DB. So I hope this flow is clear. Now the next functionality is like we have to give the provision to the user to
17:51
send the textual form of the message and to support that we need a chat server over here and for that I will be
17:58
introducing one more service and maybe the primary core functionality of our system and that is a chat service and it
18:05
is quite obvious whenever we are sending something to our chat service that information should be saved into the
18:12
database. So here we will be having our next database and that is called as the chat DB to save all the chat in our
18:20
backend. So this will be our next database called as the chat database. Clear? Now if you look carefully here
18:26
what we are telling we have to support both the textual form of the message as well as we have to support the media
18:33
file. And obviously you know we cannot save a media file into our database. And
18:38
as you know to save all the media files into our application we use a blob storage or a S3 bucket to save all those
18:46
data. So here all the textual form of the message will go into our chat database and all the media file means
18:53
the image or the videos will go to our second storage and that is a blob storage over here. And thus here you can
19:00
see we have more or less fulfilled few of the functional requirement of our system that is onboarding of the user
19:06
and number two how the user will send the textual message as well as the media file with the friends and the family. So
19:13
two of the functional requirement are already solved. Now the next thing is like we have to support the group
19:18
messaging and since I have already told you the group messaging will also follow the same path and that is with the help
19:25
of the chat server. So we do not have to do anything explicitly rather what we have to do we need another service to
19:32
manage all the groups. So here we will be having one more service called as the group service and the main role of this
19:39
group service will be to manage all the groups that are there in our system and
19:44
for that we also need an additional database called as the group DB. I hope this is clear. So here you can see we
19:51
have more or less fulfilled all the functional requirement that we have gathered over here. Now since we have
19:57
more or less identified that what will be the core entities or the core module of our system. Now let's go into a deep
20:04
dive analysis and let's see how this individual system will work over here
20:10
and how they will interact with each other because obviously here you can see I just have given a very brief
20:16
introduction that there will be a chat server which will be responsible for sending the chat from one user to the
20:23
another. But believe me this is not at all simple as it look like because there are tons of concept and many things that
20:29
you have to design in detail to fulfill all the functional as well as all the
20:35
non-functional requirement of this design. So without wasting much time, let's go into the next phase of our
20:41
designing and probably the most important phase of our designing and that is the low-level or the deep dive
20:49
designing of our system where we will see in detail that how each and every
20:54
component will interact with the database. How we will be sending a message from one user to another in near
21:01
real time. How we will be sending a confirmation message to the user means whether it has been read or it is still
21:08
pending to be delivered. All this thing we will be seeing in our next phase of our designing and that is the low-level
21:14
designing or in the deep dive designing of this system. So without wasting much
Low Level Design
21:20
time let's go to the fourth step and the last phase of our designing and that is
21:25
the low-level designing of this system. Before proceeding further, I just wanted to notify that I have created a very
21:32
simple website over here so that you get all the contents that I upload on the
21:37
YouTube on a single platform. So here you can see there are lots of content on the system designing on the low-level
21:44
system designing. Similarly, here we have the complete graph playlist where we have already 15 to 16 video over here
21:51
as well as all the latest contents that I'm uploading on the YouTube. I will keep on updating all those things in
21:57
this website. This is a free website that is hosted also in a free domain. So do not forget to bookmark this website
22:04
so that it will be helpful for you to find out all the relevant contents regarding your upcoming interview. So
22:11
let's start with the low-level designing. But before starting the low-level designing, I just want to tell you I might sound a bit different now
22:18
because I just had a a root canal and a wisdom teeth surgery. So it sometimes
22:25
sounds a bit different I know that but let's do it. So yeah so let's start with
22:30
the low-level designing. So here if you look carefully in the highle designing we have given a very brief introduction
22:37
and we have just identified that what are the major components that is needed
22:42
to serve or to fulfill all the functional requirement that we have listed over here. But in our low-level
22:50
designing, we will go in detail on each and every component and we will try to
22:55
see how each and everything will behave and how we will handle this huge amount
23:00
of traffic with this huge amount of data in real time. So without wasting much
23:06
time, let's start with the low-level designing. And the first thing that we will do, we will just copy paste the
23:12
same highle designing from here into our low-level designing section. So the
23:17
first thing first we will start with the easiest one and that is the user service. And if you have already
23:23
followed my previous video you must be knowing that this user service is mainly responsible for registering a user into
23:30
our application as well as whenever a user logs into our application. We do an
23:35
authentication based on this user DB and in response we simply give a JWT token
23:41
or a session ID so that it can call all the APIs that we have designed over here. So here also it will be the same
23:48
thing that is here we will be having our user service and as you know we have to persist the data of the user and for
23:54
that we need a user database and here also since the user data is a flat relational data and that is why we will
24:01
be going with a posgress or a MySQL database both of them will work the same
24:06
only thing is like it is easy to scale up the posgress database with respect to the MySQL database. I hope that is
24:13
clear. So what we will do here this database will be our posgress database and let's see what will be the schema
24:19
structure or what are the attributes that we have to save over here. So these are the following attributes that we
24:26
have to persist for a particular user that is the user ID, username, email id, phone number, status, last scene and
24:33
other metadata that is required. So here remember if you are creating a WhatsApp then you do not need a email id over
24:39
here. But if you are creating a messenger service at that time you need a email id to do the registration. So
24:46
based on the application that you are getting during your system designing just create the schema structure
24:52
accordingly. Here I have just shared a simple generic schema structure that will work for both the application. I
24:58
think this is quite straightforward and clear. Now let's move to the other services that we have. So here we have
25:04
the chat service. We will do it later because this is the heart of our application. So the next service that is
25:10
required is the group service. So the group service is also quite simple that is it is a service that is responsible
25:17
to create and modify a particular group. So for example whenever you are creating a group or changing any metadata of the
25:24
group this service will come into play as well as there is one more additional functionality that this service is
25:30
responsible is for example you are passing a particular group ID it will
25:36
show you or it will return what are the list of members or the user ID who are
25:41
present within the group. So these are the three or four functionality that this group service will be doing. And to
25:48
save all the metadata of a particular group, we will be simply using another database that is a group database. And
25:55
here also since it is a flattened database and a relational database that is why we will be using a posgress
26:02
solution over here also. So let's see how the schema structure of the group database will look like. So this is how
26:09
the first table of our group database will look like. So the first database is like the group DB which will have the
26:15
group id, the group name, the description and other meta that is required means when was the group
26:21
created or maybe the thumbnail of the group all those thing will come as a metadata over here. Now the second table
26:27
that we need within this group database is the mapping table means which will give us the information that which user
26:35
belongs to which group. So there will be another table within this group database that is the group mapping database. So
26:41
let's see how the schema will look like. So this is how the schema of the group mapping database will look like. So here
26:48
you can see we are having a ID which is an auto increment ID, a group ID, a user
26:53
ID, the join date and other metadata that is required. So here you can see group ID is not the unique key over here
27:00
because you can see a particular group can have multiple users over here. So
27:06
there will be a lot of repetition of the group ID with the corresponding user ID who are part of the group. So to keep
27:12
that row unique we are using an auto increment ID and that is a simple UID or
27:18
a simple id. So here we are done with the two tables that is the group DB and the group mapping DB. So here we are
27:25
done with the two major service that is the user service which is quite simple and the second one is the group service.
27:32
Now let's move to the next service and that is the chat service which is the main core of our application. But just
27:39
to give you a heads up there will be some additional service that is also needed over here to fulfill all our
27:46
requirement. But since we do not know as of now that what are the additional services that we need. So we will not
27:52
discuss it as of now. But as we progress we will keep adding all the services that is required. So now let's go to the
27:59
next service and probably the most crucial service and that is the chat service. Now before designing this chat
28:06
service let me give you a small concept of what are the different types of connection that we use in our system
28:13
designing or in the real world application. So as you know whenever you are calling a particular service using a
28:19
load balancer means with this simple approaches there we use a HTTP connection means we send a request to
28:27
the server and in return the server gives you some response. So that is a unidirectional communication which is
28:33
called as a HTTP connection. Means you can only send a request from the client to your server and the only
28:40
functionality that a server can do is just give a acknowledgement or a response in return. Now the second type
28:47
of connection is like the long pulley means the client make a call to the backend server and if the response is
28:55
not present in the backend system immediately a connection is kept on hold
29:01
and once the data is received by the server at that time the response is given through that connection means
29:08
there is an open connection that gets established between the client and the server in case of the long pulling
29:14
connection. So the first one was the HTTP connection. The second one is the long pulling connection where a client
29:22
makes a request to the server and it wait for the server to give a response in return for a predefined amount of
29:29
time. So that is the concept of the long pulling. So here we are having a small duration of a open connection in the
29:36
long polling communications protocol. So that is the major difference between the HTTP and the long polling communication.
29:43
Now the next type of communication that is possible is called as SSE that is
29:49
server send event. This is also a unidirectional connection. But only
29:54
difference between the HTTP connection and the SSC is like for HTTP a client
30:00
can make a request to the server. But in case of SSC a server sends a response to
30:05
the client. So it is like a push back notification that a server send to all
30:10
the registered client. So that is the difference between a HTTP and a SSC
30:16
connection. So for example there are some processing or the event that are generated on the back end at that time
30:21
to send a notification to the client this SSC comes into play means the server send a notification to the front
30:28
end that some data are available in our back end and based on that all the subsequent calls are done. Now the next
30:35
type of communication that is present is called the websocket connection. And the main advantage or the behavior of this
30:42
websocket connection is it is a full duplex connection. Means a connection is
30:47
persistent between a client and a server for a long time and whatever the data
30:53
that gets generated in the server can be sent to the client in real time. Means
30:58
there is no waiting time for the client to send a request to the server. Similarly, there is not a delay for the
31:05
server to send the response to the client. And since this is a duplex connection means this sending and
31:10
receiving of the message can happen at the same time. So this is a very important knowledge that you have to
31:16
know for designing this system. Now let's see what can be the appropriate connection protocol that we will be
31:22
using to implement this chat service. Now if you look carefully the chat what
31:28
we do is on the real time mean you are typing some messages and you are just sending to your friend. Similarly your
31:34
friend is giving a response in return. So there is a birectional connection that is happening on a real time. Now if
31:42
you look carefully if we are going with a HTTP connection what will happen to send a particular message from the
31:48
client to the back end what we have to do? we have to simply send a request from the client to the backend service
31:54
using a post call and thereafter to get the response for that message we have to again make a HTTP get call to retrieve
32:02
the response from the friend. So each and every time you are posting something in our back end means you are sending a
32:08
message thereafter you have to keep on retrieving the data with the help of the get call for a infinite amount of time
32:15
means to get any response from our friend we have to send any number of HTTP get request to get all the
32:22
messages. So that is actually not possible in the real life mean for example your friend is not replying you
32:29
then there is no reason of sending a HTTP get call to get the response because in the server side there is no
32:36
data for you to fetch. So that will be a simple unnecessary get call that you will be doing to retrieve the data and
32:43
that is why we cannot go with the HTTP connection. I hope this is clear. Now the next thing is like the long polling.
32:50
So here if you look carefully we can go with the long pulling approach. So here what will happen? So for example you
32:56
want to send a text to your friend you will simply submit the data to our server or to our back end with the help
33:03
of the HTTP call. So a simple post call will go with the help of a HTTP post
33:08
call and it will get submitted to the database. And to get the reply of your friend what we will do, we will simply
33:15
do a long polling. Means we will simply open up a connection for a particular amount of timeline and if within that
33:22
timeline your friend replies you back then those amount of information will come in response and it will be shown
33:29
into your UI. So that can be done but look carefully if we are going with the long pulling approach there is a very
33:36
critical problem that will happen. So for example you do not know that after how many amount of time or at what time
33:43
your friend will reply. So it is not possible to open up a long polling
33:48
session for a infinite amount of time. So for example a long polling connection will remain persisted for 30 second. So
33:56
you cannot do that for first 30 seconds you will open up a connection with the hope that your friend will reply within
34:02
that 30 secondond. Now again after 30 second it will terminate. Then again you have to send one more request with again
34:08
the same hope that he will reply within 30 seconds. So in this way there will be multiple requests that will go from the
34:16
front end to the back end and all this connection will be open until and unless you receive a message from your friend.
34:23
So this connection is also not possible in the real life scenario. Now comes the
34:28
third one that is the SSC connection. So this one can also be done. So let's see what can be the pros and cons for this.
34:35
So to implement a chat service using a SSC connection what you have to do you have to simply send the message with the
34:42
help of the simple HTTP connection with the help of the post body. And once you send the message to the server as soon
34:49
as your friend replies you back a simple notification will come from the back end
34:54
to the front end with the help of this SSC connection means a notification will come up that you got something in your
35:01
mailbox and thereafter you have to again make a call to your back end to fetch that information. So here you can see
35:07
you are making at least two to three calls to send and receive a message from a friend which is also not possible in
35:15
the real life because opening up this much amount of connection for a application which handles a billion of
35:22
user is actually not possible. So the last but not the least we have the websocket connection and here what
35:29
happens is like since the websocket is a birectional connection means at a
35:35
particular event of time both you and your friend can talk simultaneously on a
35:40
single connection means you do not have to check repeated number of time that whether there's a data in the back end
35:46
or not or you do not have to do a separate HTTP connection to send the message and then you do not have to wait
35:52
for another reply from the server. So it is a single connection that will serve both the purpose of receiving and the
35:59
sending of the text message from you and your friend. So that is why here we will
36:05
go with the websocket connection to implement the chat service that we have to design over here to serve all the
36:12
text messages in near real time. I hope this is clear that why we have to go
36:18
with the websocket connection rather than a simple HTTP or a long pulling connection. So I hope this is clear. Now
36:25
since you have understood that why we are going with the websocket connection let's now see how we will do it. So what
36:32
we'll do we have to get rid of this one and we will just create a websocket service out of this one. So here we have
36:40
the chat service which is running on a websocket connection and obviously since this is a micros service application and
36:46
we are supporting a millions of user over here. So it's quite obvious that
36:52
there will be a lot of replication of this websocket service in our back end.
36:57
So let me create one or two application over here. So this will be all our chat service and obviously when we are having
37:04
a multiple service in our back end we need a load balancer or a API gateway to
37:09
handle that and for that what we need we need a dedicated websocket gateway or a
37:15
websocket load balancer over here. So in modern technology more or less all the
37:20
load balancer that are available in the market support both HTTP as well as the websocket connection within the same
37:27
load balancer. But since here our chat service is highly dependent on the websocket connection. So it is highly
37:34
recommended to have a simple dedicated load balancer that only support the
37:40
websocket connection. So what we will do here we will create one more load balancer or a websocket gateway to
37:47
handle this functionality explicitly. So here we will be having a simple load balancer which will only support the
37:54
websocket connection and the responsibility of this load balancer will be saved that is the authentication
37:59
and authorization the rate limiting and proper routing. So let me list down all those things over here. I hope this is
38:06
clear that why we have segregated these two load balancer one for handling the HTTP request and one for handling the
38:12
way connection. Now what will happen all these user or the client which are present over here will talk to both the
38:19
gateway that is present that is the API gateway and this websocket gateway and how they will communicate based on the
38:26
API endpoints that we are providing. So here if you look carefully whenever we were doing the API designing here all
38:33
these call that we have defined are post and get and all of these are normal HTTP call but here when we are sending the
38:41
message this was a websocket connection and whenever there is a websocket connection the connection will go
38:47
through this websocket gateway. So what will happen all the clients or all the user will chat with each other with the
38:55
help of the websocket connection and through this websocket API gateway. So all the connection over here that is
39:01
present over here are basically a websocket connection. Now what will happen once the request comes to our
39:07
gateway it will simply route the traffic to the corresponding chat service. But remember this is not at all easy the way
39:14
it looks like because of the fact if you remember I told you a websocket connection is a duplex connection and it
39:21
is an established connection means it is like a path or a highway that will be open until and unless you are done with
39:28
your chat. So for example you are using the WhatsApp for 1 hour means that connection should be open for 1 hour and
39:36
to establish that persistent connection this websocket have to be super intelligent. So for example whenever the
39:42
user one is trying to chat with user two so user one have to open up a connection
39:48
with the chat service one. Similarly a user two always have to open up a
39:54
connection with the chat service two. And if this connection is not persistent
39:59
then what will happen the delivery of the message will fail. So we will discuss all this thing in detail and we
40:06
will see why a sticky network or a sticky connection is needed over here to
40:12
establish a websocket connection and we will also discuss how we will do that. Now let's move to the next phase that
40:19
how the communication will start. So what will happen? So let's take an example. This is user one and this user
40:25
one want to talk to his friend which is user four. So what happen is like
40:30
whenever the user one login to our application a login authentication request will go to the user service
40:37
means he want to start a new chat and here once the credential is matched and the request is authenticated this user
40:44
service will send a GWT token or a session token to this user one. So what
40:50
actually happens is like once a client or the user want to start a conversation he have to first request for a websocket
40:57
connection and how it is done a initial HTTP request will go from the client to
41:03
the server means it is a simple HTTP request that will come to this load
41:08
balancer. So a request come from the client to the server with a request that
41:13
I want to upgrade my HTTP connection into a websocket connection. So by
41:19
default you cannot open a websocket connection. So to get or acquire a websocket connection what you have to do
41:26
first you have to ask for a websocket connection making a simple HTTP call and
41:32
once the request goes to the server the server does a validation and handshaking
41:37
and once this acknowledgement or the handshaking is done successfully with the server thereafter only a birectional
41:45
websocket connection gets established means at step three only you can send
41:50
and receive message together but before that it is simply a HTTP call that you
41:56
are initiating. So the real fact is all websocket connection are basically a simple HTTP call at the very beginning
42:03
and once the handshake has been done then that HTTP call gets upgraded to a birectional websocket connection. So I
42:11
hope this concept is clear that what is the difference and how a websocket connection gets established. Now comes
42:18
to the next thing that is how we should persist this websocket connection and why it is needed to have a sticky
42:25
websocket connection. So here what will happen once the user have done the handchecking and everything he or she is
42:32
ready to send the text to his friend. So what he will do using that websocket
42:37
connection he will simply send a message to his friend. So let's take an example that within this websocket connection he
42:44
is making a request called as send. And here for example the user is passing three things that is number one the
42:50
message he want to send number two the originator means who is sending the message and the next parameter is who is
42:57
receiving the message means for example I'm sending the message from user one to user four then the third parameter will
43:04
be user four means this message is dedicated to user four I hope this is clear so a text message got sent from
43:11
user one to user four and this is the message that got send. Now remember I
43:17
told you each and every user is connected to different chat service. So for example user one here is connected
43:24
to the chat service one and user four is connected to chat service 2. So here the
43:30
chat service one first have to know that where this user 4 is located and based
43:35
on that it will forward that message from chat service one to chat service 2.
43:40
So there should be a mapping between the user ID and the chat server where it is
43:46
connected. I hope you got the idea that why we need a sticky or a onetoone
43:51
communication over here. Still if you do not understand do not worry as we proceed further it will be damn clear
43:57
for you that how we are doing it and why it is needed. So what we have to do we
44:03
have to create a mapping between the user and the websocket connection it was earlier connected or it will going to
44:09
connect. So what we'll do here we will simply create a mapping object. So here the user one for example is connected
44:17
with an open connection that is the websocket connection one. Similarly the user two is connected to another
44:23
websocket connection that is websocket connection two and so on. So in simple
44:28
term just understand like this to start a conversation within the WhatsApp first thing that you need is a websocket
44:35
connection object. So this is nothing but a connector object that is required to start any conversation within the
44:42
WhatsApp until you are active in the WhatsApp this connector should not die.
44:48
So that is the main fundamental thing that you have to remember. Now the question is how we will save this
44:54
information. So here if you look carefully what is happening is like user one is trying to do a chat with user
45:00
four. So what will happen? It had already opened up a websocket connection and here this chat service have received
45:07
the message from user one. Now this chat service will try to search over here that in which open websocket connection
45:14
where user 4 is connected to. And for that what he have to do it have to make a request into this mapping object and
45:21
it have to locate where this user 4 is actually located. And as soon as it find
45:27
that the user 4 is connected to websocket 2, then what it will do? It will simply send the message from the
45:34
chat service one to the chat service 2. And this chat service 2 will simply send
45:40
that message from this chat service to user 4 using the simple websocket connection that is already opened. I
45:47
hope this is clear that how the communication is getting established and how we are sending the message from one
45:54
websocket connection into other. Now the thing is like how we should store this message. So here if you look carefully
46:01
for each and every message that you are sending we have to scan this entire object and to make it efficient and
46:07
provide less latency we will keep it in a cache service called as a radius
46:13
cache. So all this information about the connection we will keep it within our
46:19
radius cache over here and this is nothing but a websocket registry that we
46:25
are creating over here. So if you just go through the documentation of all the websocket connection you will see that
46:31
each and every websocket connection or a ecosystem will have a websocket registry
46:37
where it have to persist the information that which user is connected to which websocket connection. So here we are
46:44
establishing that only. Now as I have told you before the way the traffic is
46:50
sent from the websocket gateway to this chat service though looks simple over here it is actually not simple because
46:58
for example the user one is connected to the websocket connection one and in
47:04
between somehow this websocket connection gets terminated or it gets disconnected maybe because of the
47:10
network. Now when the second time this user one wants to establish the
47:16
connection with our backend service means with the load balancer this load balancer have to send that user one to
47:24
that web connector it was opened earlier. So this websocket gateway will
47:29
also talk with this radius cache or with this websocket registry to see that
47:35
which user is connected to which websocket connector. So here the gateway
47:41
is intelligent enough to route the traffic to the corresponding websocket server where it requests to send. Now
47:48
the question might arise that is it possible to keep all this websocket
47:54
connection open for a indefinite period of time for each and every user. So for
47:59
example here we have assumed that we have 1 billion user over here. So it is
48:05
obviously not possible to open up 1 billion websocket connection into our
48:12
packet because believe me websocket connection is very heavy weight and it
48:17
consume a lot of bandwidth and memory. So it is not possible to open up 1
48:22
billion websocket connection over here. So what we do here for each and every
48:28
open websocket connection there will be a TTL present over here and TTL means
48:35
time to leave means if you are not active in our system means if you are not active in the WhatsApp for maybe 1
48:42
minute or so this websocket connection will get deleted from this websocket
48:47
registry and that is why here we have to provide a TTL for each and every
48:53
websocket connection that is open and present within our websocket registry. I
48:59
hope this is clear. Now the next question will arrive is for example two friends are chatting over here. User one
49:05
is chatting with user four. Now suddenly in between user four dropped off or it
49:12
network got disconnected. Then what will happen after a minute or so this open websocket connection will get deleted
49:18
from this registry. Now again after few time once the user 4 comes to our application and resume with the
49:25
conversation what will happen another request will go to the websocket service over here and at that time it will see
49:32
that there is no predefined open websocket connection that is present. So
49:37
what will happen a new connection will get established over there and that new
49:42
connector will get registered within our websocket registry. Now there is a
49:47
critical problem with this approach that is for example these two friends are chatting with one another. Now user one
49:55
sends a message and user four logs off or maybe for example user one just want
50:01
to send a textual message to user four who is offline. So here what will happen
50:06
a request will go to this chat service that I want to send a message from user one to user four and this chat service
50:13
will see that user 4 is not active in our system or there is no websocket
50:19
connector that is already present over here. So what it have to do then at that
50:24
time to handle all those offline user it have to persist that information into
50:30
our database so that once the user phone comes active in our application at that
50:36
time we can send that message to user 4. So here what we'll do here we have to
50:42
submit all our data into our database and how we will do it. So since here we
50:48
are having thousands of requests submitted in our back end per second. So it is not possible for a particular
50:55
server to persist all those information in our DB. So for that what we need we
51:00
have to go with the approach of the eventdriven service where we can push all the textual messages that we have
51:06
received from the user. So here basically we need a event streaming platform where we can submit all the
51:13
datas that we are getting from the front end to the back end. So here what we'll do we need an additional service that is
51:20
nothing but a radius stream. Now here you can see we have multiple options that are open for a streaming platform.
51:27
We can go with a Kafka streaming or we can go with a radius streaming. But let me tell you why we have used a radius
51:34
streaming rather than a Kafka streaming or a Kafka broker over here. So if you do a homework you will get to know a
51:40
radius streaming platform is super lightweight and the latency of the radius streaming platform is quite low
51:48
than a Kafka broker means the latency of the Kafka is more than that of the
51:54
radius and that is why since here we are creating a chat service and here the
51:59
minimum latency is quite crucial and that is why we are using a ready streaming platform rather than a Kafka
52:06
stream and what it will do Here we will simply send all the messages that we are
52:11
getting from the front end. And here in the radius we have the concept of the
52:16
channel just the way we have the concept of the topic in Kafka. Similarly in radio streaming we have the concept of
52:22
channels means each and every chat service will get subscribed to a
52:28
particular channel that we have over here. So here since the user one is trying to send a message to this user
52:34
four what will happen? This chat service will send the message to the channel
52:39
where user four is subscribed and where users four is subscribed user four is subscribed to websocket 2. So here the
52:47
message will go to the channel two since user four is subscribed to that. I hope this is clear. So what is happening the
52:54
all the message are there within our radius cluster but we have to persist it in our database and for that what we
53:01
have to do we have to write a consumer service to consume all the messages from
53:06
here and post it into our chat DB. So here we will write another service
53:12
called as a message service and this message service will submit all the data
53:17
into our chat database that we have defined over here. So all this data will
53:23
come to the chat DB that we have defined. I think this is clear. So here all the message first coming to this
53:30
radius and thereafter it is getting persisted in our chat DB with the help of this consumer service that is the
53:37
message service. Now let's see how this chat DB will look like. So if you understand the problem statement this
53:43
chat service should be highly rightheavy means whatever the thousands and
53:49
thousands of chat that gets submitted within this radius should get persisted
53:54
within this chat DB also and that is why this DB should be highly right optimized
54:00
and the best right optimized database that we have is the Dynamo DB or the Cassender database. So here we are
54:07
having the chat DB and this will be a Cassandra database. And now let's see how the schema will look like. So this
54:13
is how the schema will look like. Here we have a chat ID, a message ID, a sender ID, a receiver ID, the message,
54:20
the type of the message, the timestamp and the delivery status. So you must be confused that what is the difference
54:26
between the chat ID and the message ID. So chat ID is nothing but one toone mapping means user one is connected to
54:33
the user four. So that is chat number one. Similarly, user one is connected to user three that is chat ID two. So that
54:40
is basically the chat ID and whatever the message that you are typing within the chat is nothing but the message ID.
54:48
So I hope this is clear and obviously this also need an auto increment ID and here we can provide a UID or a UU ID
54:56
over here and here you can see I have also mentioned the type that it can be a text message or a image message over
55:03
here. Now how we will send the image message that we will discuss shortly and also how we will update this delivery
55:10
status that we will also look very soon. Now let's go to the another main important thing is like for example you
55:16
want to send the message from user one to user four and user four is right now
55:22
offline. So if you know the feature that once you get a message from your friend and you are offline you get a
55:28
notification into your message. So somehow we have to send a notification to all the offline user that you have
55:35
received a text message. So what will happen once the user one sends a message to user four if the user 4 is not active
55:43
at that time we will simply send a notification to user 4 and for that we
55:49
need another service here as a notification service. And since here we
55:54
are developing a mobile application. So we have to support both Android as well as for the iOS device. So FCM stand for
56:01
Firebase cloud messaging and APN stand for Apple push notification service. So
56:07
this supports Android and this supports iOS. I hope we are almost clear with how we are sending message from one friend
56:14
to another. Now the next thing that we will see is how to send the group
56:19
messaging. So let's see and let's go into the deep dive analysis of how we have to send the group messaging with
56:26
the same schema structure or the same design structure that we have done till now and believe me if you have
56:32
understood a bit that how onetoone messaging is happening over here implementing or designing the group
56:38
messaging is pretty straightforward. So what happens in the group messaging is like for example this is user one and
56:46
the user one is trying to send a message to a group. So what actually happens in
56:51
the back end is like once the request comes to this chat service, the chat service in turn makes an API call to
56:59
this group service to see that who are the members that are present within the
57:04
group. And if you have remembered for that we have created this group service that is based on a particular group ID
57:11
it will retrieve who are the member of that group means what are the user ID of
57:17
those member present on that group and once we have the complete list of all the user ids that are present within
57:24
that group what we have to do we have to actually individually send that message
57:30
to each and every member of the group. So it might look from the front end that
57:36
it is just like a simple broadcast to the group channel but actually it doesn't happen. What actually happens is
57:43
individually we have to send message to all the members of the group because if you look carefully to the interface of
57:49
the WhatsApp application there you can see which are those member who have read the messages who have not received the
57:56
messages and who have received the messages but not read the messages. So to give that amount of precise
58:03
information we have to send all the messages to each and every individual that are present within the group. And
58:10
how we do it? It is very simple. Once the group message comes to our chat server means here we make a call to this
58:17
group service which will return all the list of user that are present within the group and based on the total number of
58:25
users we have to keep an iterator over there and based on that user ID we have to check that whether that user is
58:32
active or not and if it is active then it will be present in our websocket
58:37
registry and thus taking the websocket connector from here We have to send that
58:43
message to that respective client or the respective user. And if that user is
58:48
offline then what will happen that entry will not be present within this web soocket registry and thus it will get
58:56
persistent in the DB using this flow means it will go to the ready stream and from this registream it will get
59:02
consumed by the message service and there will be a push notification that will be sent to that user. I hope this
59:09
is clear. So in case of a group message both the scenario can happen means some of the user will be active whose
59:15
websocket connection we will receive from this websocket registry and few of the members will be deactivated and will
59:22
be away from the network and for that to implement that offline support we have to save it in the database. I think this
59:29
is clear that how with the help of this onetoone messaging service we are implementing this group support. Now
59:36
let's see some different aspect of this messaging that is how to send a image or
59:42
a video in the message. So remember whenever you are sending a image or a
59:47
video in our messenger or in the WhatsApp service there the data is not get uploaded in the back end with the
59:54
help of the websocket rather what happens it follows the same uploading fundamental that we do for a image
1:00:00
upload for a website means it gets uploaded with the help of the API call means whenever you are sending an image
1:00:07
or a high resolution picture that file gets uploaded in the backend with the help of a file uploader the service. So
1:00:14
what happens is like once you upload a image the request come to this load balancer and here this load balancer
1:00:21
will call a image uploading service. So here we will be having a image or the
1:00:27
media upload service and this media upload service will be responsible to upload any highquality image or a video
1:00:35
into our server and obviously as you know we do not store any highquality images or the video in our normal
1:00:42
database. What we do we use a blob storage for that and thus this data will
1:00:48
get persisted in a different storage mechanism which is nothing but a blob storage. Thus here we will consider a S3
1:00:55
bucket to store all the images and the video that we are uploading in our backend server. And what happens in the
1:01:02
response once the video gets uploaded successfully or the uploading process begins this media upload service will
1:01:10
return a image URL of this S3 bucket. So the response of this media uploader
1:01:15
service will be a image or a video URL. And once the user or the client receive
1:01:21
this video or the image URL as the response of the video upload that URL
1:01:26
actually get persistent in our chat DB using this service. Means once the video
1:01:32
gets uploaded in our back end in the S3 bucket a simple message request will go
1:01:37
with the help of this web soocket. And here in this case instead of this message what we will send we will send
1:01:45
this image or the video URL and thus this will get delivered to the client
1:01:50
where we want means in the chat database here you can see here I have given the attribute called as message. So this
1:01:56
will consist of the image or the video URL. So this can be a text message or it
1:02:02
can be a image or a video URL. And here in the type we will mention it accordingly. So here we are almost done
1:02:09
with everything. Now the next feature that we have to do is like whenever you are opening a particular chat you can
1:02:16
see there at the very top end you will get a provision to search a particular message within the chat. So we have to
1:02:23
provide a search service so that a user can search a particular keyword or something to search a particular message
1:02:30
within the chat. And to implement that obviously we need a search service and here to search a particular keyword from
1:02:37
this billion of messages obviously we need a elastic search. So here we will
1:02:43
define another service a message search service. So here the request will come to this message search service and from
1:02:50
here it will call a elastic search that we have over here and this elastic
1:02:55
search will query the chat database that we have over here. So whatever the
1:03:01
message we have within the chat database this will be read by our elastic search
1:03:06
and thus it will give the response based on the keyword and how the data will go from the chat service to the elastic
1:03:13
search. I hope you know that right now by seeing all my previous video that is with the help of the CDC pipeline. So I
1:03:20
think that is clear and also remember this chat or the messages that we are retrieving over here might consist of
1:03:26
images or the video. So this search service also have to talk to this blob storage to retrieve the corresponding
1:03:33
video or the images from the server. Now there is a small bit of optimization
1:03:38
that we have to do that is for each and every time the video or the image that
1:03:43
we are getting in the display we cannot pull it from our back end. So to optimize that to save the latency of
1:03:51
this one what we have to do we have to implement or we have to introduce a CDN.
1:03:57
So as you know what is CDN? So CDN is nothing but a server that is present
1:04:02
geographically into your location. So that whatever the image or the video all the media file all the codes are present
1:04:09
nearby to your location so that the time to fetch the data get minimized. So here
1:04:15
what we will introduce here we will be introducing a CDN library. So all the
1:04:20
user will first connect to the CDN library that to see that whether the images is present on the local server or
1:04:27
not and if there's a miss on the local server means if it is not present on the CDN then a round trip will happen from
1:04:34
this CDN to this S3 bucket and thus our CDN will get updated. So I hope this is
1:04:40
clear that how we have introduced a CDN over here to reduce the time to fetch a
1:04:46
particular image or the video in near real time. Now one more thing that is
1:04:51
for example you opened your WhatsApp application now you want to scroll down all the messages that are there in the
1:04:57
history. So what you have to do we have to fetch it from our back end and for that also we will be using the same
1:05:05
service that is the message search service which will retrieve all the previous messages for a particular chat.
1:05:11
So here if you remember we have created an API endpoint that is this one to fetch all the messages for a particular
1:05:18
group and the message used to come in the form of the lazy loading or the pagionation. Similarly for the onetoone
1:05:24
messaging the same thing will happen means once the user want to fetch the old data it will come to the user with
1:05:30
the help of this service that is message search service but there is one thing that is WhatsApp claims that they do not
1:05:37
persist any data for the user means according to them they do not have a
1:05:42
database in the back end which persists all the message or information. So how do they do
1:05:48
it? Gimmick. But yeah, how we can do it is like here if you see we have the user
1:05:55
service and this user are nothing but a client. So and each and every client is nothing but a mobile device and within
1:06:02
the mobile devices we have the local cache within the memory and it is possible that all those messages are
1:06:09
persisted locally within the WhatsApp folder with the help of some storage mechanism. So if you are familiar with
1:06:16
the Android development there we have the provision to save some messages in the local. So maybe with the help of
1:06:22
that feature they keep on saving all those information in the local memory. So that the fetching time of the
1:06:29
previous record or the fetching type of the messages decrease significantly because obviously at that time you do
1:06:35
not have to make an API call to retrieve the previous information and because all the information or all the messages are
1:06:42
there in the local. So at that case we do not need a message service to fetch all the information that is not present.
1:06:49
I hope this is clear that how we can optimize this also. But here if you just want to remove this shared database
1:06:55
completely obviously this is not possible because all those unsend message means those messages which need
1:07:02
to be sent for the user who are not active at that moment have to be saved
1:07:07
somewhere. So it cannot be saved for a undefined amount of time in a ready
1:07:12
string. So it have to be stored somewhere and for that we have to use a chat database in the back end. But it
1:07:20
might can happen that once the message has been sent successfully to the user
1:07:25
once they are active at that time we will delete that message from the database. But that is the way to
1:07:31
optimize the database but I'm not sure how they do it in the back end. I hope this is clear that how we can get rid of
1:07:38
the chat database or how we can reduce the size of this chat DB because obviously there will be trillion and
1:07:44
trillion of messages and if we keep on persisting all the messages that will be a huge load for the back end. So I have
1:07:52
pretty much covered everything but let's go a bit deeper because there are few
1:07:57
more functionality that are still pending and that is number one how we
1:08:02
will show it to the user that a particular user is online or not and if
1:08:07
you have understood this designing properly you can easily understand that whoever is active on a particular
1:08:14
instance of time for that user the websocket connection should be also active means His entry should be present
1:08:22
on this websocket registry. And if the entry is present on this register then
1:08:28
we will say that that user is online. And as soon as this user gets offline
1:08:33
means after some time once this detail is over obviously the record will get deleted from here. And based on that we
1:08:40
can showcase that this user is not active and it was active till a particular time frame. And how we will
1:08:47
get that time frame that is we have to update this last scene variable that we have within the user database. So what
1:08:55
we have to do we have to make a connection between this user database and between this radius cache. And how
1:09:02
we will do it? We will also implement a CDC pipeline over here. So that whenever
1:09:07
there is a change over here means whenever there is a timeout that happens for a particular websocket connector
1:09:14
here we will send a notification to our user management service that this user
1:09:19
is not active over here and thus here you just update the last scene over here
1:09:24
for the user. So I hope this is clear. So here we will be having a user management service and this user
1:09:31
management service will update the user status means whether he's online or not and what was the last scene of that
1:09:37
user. So here with the help of this websocket registry we can track a particular user. Now at the very end
1:09:44
there is a small bit of piece that is still pending that is for example a user
1:09:49
is offline and once he comes online how we could retrieve all the messages or
1:09:55
how we can retrieve all the unsended messages for the user and for that what
1:10:01
will happen once the user gets a websocket connector over here it will go to the chat service and this chat
1:10:07
service have to call that whether there is any pending messages for this user or
1:10:13
not. So here we will be having one more service called as another message
1:10:18
service and this message service will fetch all the messages means all the
1:10:24
unsend messages from this chat DB. So this will retrieve all the unsend messages and obviously all the messages
1:10:30
will have the sender ID and the receiver ID. So we can easily find out who have sent the messages, what is the message
1:10:36
type and all those things. So it is pretty straightforward. So here if you look carefully we have almost we have
1:10:43
almost covered everything that we have taken into consideration in our functional requirement. The only thing
1:10:49
that is pending is like we have to give the delivery and the read receipt. So that is quite simple that is here
1:10:57
whenever you are using a websocket connection using that websocket connector only you can easily give an
1:11:03
acknowledgement that whether you have received the message or not means when the server is sending a message to the
1:11:09
client it can simply get a not acknowledgement that it have received the message means it will be a double
1:11:14
tick and once the user have opened the message then the front end have to send another notification to the back end
1:11:21
means to the server that that message has been and thus it will mark it as double tick and thus here we will update
1:11:28
delivery status to red means it is successfully delivered and the status is red. So here we have covered each and
1:11:36
everything that is required more or less to create a WhatsApp application or
1:11:41
create any chat application for your system design. So I hope you have
1:11:46
thoroughly understood this video until now. So just to give you a simple understanding of this complete
1:11:52
architecture, let me tell you in short that how the data flow will work. So let me give you a data flow diagram of the
1:11:59
steps so that it will be very easy for you to understand that how the connection are getting established, how
1:12:05
we are retrieving the messages and how we are sending the message. So let me give you the data flow of this design.
1:12:11
So this is the complete data flow of our design. So I will request you to pause this video over here and go through this
1:12:18
entire steps one by one so that it will be easy for you to understand by yourself that how the data is flowing
1:12:24
across the application and after that I will explain you how the entire system is behaving. So the first thing that is
1:12:31
happening is like once a user comes to our WhatsApp platform it have to first register to WhatsApp and for that to
1:12:38
register that user we have this user service. So with the help of the user service we are onboarding a member in
1:12:44
the WhatsApp community. Next what we have to do once the user logs in with the credentials means with the phone
1:12:51
number then what is happening? The first thing that is happening is like the call is going to our backend application and
1:12:58
our backend application is checking that whether there exist an open websocket
1:13:03
connection for the user or not and we are using this radius cache or the websocket registry to get that
1:13:10
information. So if the user is coming for the first time or he is coming after a long time so obviously there will be
1:13:17
no active open websocket connector and if it is not present within this registry then what is happening the same
1:13:24
HTTP request will get converted to a websocket connector and once it gets
1:13:29
converted to a websocket connection a entry will get inserted within this registry that is the mapping between the
1:13:36
user ID and the websocket connector that got established. So right now our user one is successfully logged in into our
1:13:43
WhatsApp environment. So the first step that happens is like the establishment of the websocket connector and as soon
1:13:50
as that is done what we have to do we have to check whether there is any undelivered message for that user or not
1:13:57
and for that what will happen the call will go to a chat service and this chat service will call this message service
1:14:04
to retrieve all the undelivered message for the user want. So it will scan this
1:14:09
entire chat DB and it will try to retrieve all the uns messages with the help of the user ID and the delivery
1:14:15
status. So this message service will retrieve all the unsend message and it will simply return those messages with
1:14:21
the help of the websocket connection to user one and as soon as the message got delivered another acknowledgement will
1:14:28
come from the client means user one to update the delivery status of that messages to double tick means the
1:14:34
message has been sent successfully to the user and thus here the status will change from unsend to send. Now as soon
1:14:42
as the user one opens the chat and read the messages another acknowledgement will go by a websocket connector into
1:14:48
the chat service that the message has been read successfully and thus we have to change the delivery status from send
1:14:56
to red. Clear? And all this data is flowing across this websocket connector through this ready stream. So we are
1:15:03
right now done with onboarding our offline user into our application. Now what is the next step? The next step is
1:15:10
he will start the conversation with the friend and for that what it will do it will simply send a text message to his
1:15:16
friend. So using the same websocket connection it will send a message to his friend for example user four and as soon
1:15:24
as the message is received by the chat service the chat service will see that
1:15:29
whether user 4 is also active or not and if he is not active what it will do it
1:15:34
will send it to the ready stream to the offline channel means this user are offline right now and once the message
1:15:41
gets sent to this offline channel two things will happen number one this message service will consume that
1:15:47
message and will persist it in our chat database and number two a notification message will go to that user that you
1:15:55
got some new message in your inbox. Clear? So this is how we are managing that how to send a message to a person
1:16:01
who is offline. Now let's consider that the person whom you're trying to send the message is online and how we can
1:16:07
determine that whether the receiver is online or not. We can easily do it with the help of this websocket registry. And
1:16:14
if the user is online, what we have to do? We have to check that which websocket connector it is connected to.
1:16:20
And based on that, we have to push the message to the ready stream to that channel. So for example, the user two is
1:16:27
present in this chat server and it is subscribed to the channel 4. So here the message that has been sent by user one
1:16:34
will go to the channel 4 of the registry. So that this chat service where user 2 is located can consume the
1:16:41
message from this channel 4 and can send it to the user and as soon as it gets
1:16:46
sent to the user we have to also send an acknowledgement to the user one that user two have already received the
1:16:52
message. So all this acknowledgement will be done with the help of this websocket connection. Now what next that
1:16:58
is how we can send a group message and the way we send a group message is pretty easy that is here instead of
1:17:05
sending the message to a particular individual we mention the group id where we are trying to broadcast the message
1:17:12
and here in the place of the user for we will have the group ID and what this chat service will do the chat service
1:17:18
will call this group service to get all the list of user that are present within this group and based on that it will
1:17:26
again do the same thing that is that is fetch all the user ID from that group and then it will check the availability
1:17:32
of the user using this websocket registry and if the user is available it will then and then the message will be
1:17:39
delivered to the user otherwise it will get persistent in the DB and it will be marked as unsend. So this is how the
1:17:46
entire thing will happen and obviously all these messages will be sorted with the help of the timestamps so that the
1:17:53
user get a synchronized message in the front end. I hope we are clear and we have thoroughly understood that how we
1:18:00
should implement a WhatsApp or a chat messaging service with this video. And
1:18:05
if you have found this video useful, do not forget to like, share and subscribe to my channel and hit the bell icon so
1:18:12
that you never miss an update from my channel and you are always ready for your next interview. So see you on our
1:18:18
next video. Thank you. [Music]

