0:03
[music] Hello guys and welcome back to my channel AW with Bunny and we are back with another video on system designing
0:09
playlist and the topic or the system that we will be designing today is one of the most requested topic in my
0:15
YouTube channel and that is the payment gateway. But before proceeding or before starting with the designing of the
0:22
payment gateway, we have to know some of the basic things about the payment because this payment thing is a huge
0:28
topic to discuss and it is not possible for a person who is not from this
0:34
background to know each and every flow or each and every pattern of the payments. So before proceeding into this
0:40
payment domain or before we start with designing this payment gateway, I will give you some of the important things
0:46
that is actually needed to design this system. So the first and the foremost
0:51
thing that you need to know before designing this is what is the difference between a payment gateway and the
0:58
payment processor because unless and until you do not know the exact definition of the payment gateway and
1:04
the payment processor you will set a wrong expectation from this video as well as during your interview if you
1:10
face this question at that time you won't be able to gather the functional or the non-functional requirement
1:16
clearly. So let's start with the first topic or the first knowledge that you need to know and that is the difference
1:22
between a payment gateway and a payment processor. So here if you look carefully these are the two definition of the
1:29
payment gateway and the payment processor. Let's understand it first. So a payment gateway is a platform that
1:35
collects payment details from the user secure and tokenize them and then orchestrate the transaction flow and
1:42
communicate with the payment processor. I know you are not clear with what it actually means. I will tell you very
1:48
soon. Whereas in case of the payment processor, a payment processor is a financial network entity that actually
1:56
talks to the bank and the card network to authorize, capture and settle the
2:01
money. So basically what actually happens the entity or the system who
2:06
actually does the real transaction with the bank who actually talks with the
2:12
bank is nothing but the payment processor and whereas a payment gateway is an orchestration engine which
2:18
actually captures the user data for example the card number CVB number and all these things and thereafter it
2:25
secures and tokenize and once it tokenize everything it send that token or the packet to different payment
2:32
processor as required. So that is the main difference between the payment gateway and the payment processor. So
2:39
here in this video also we will be discussing the payment gateway. We are not dealing with how the money is
2:45
getting debited or credited from the bank and all those things. I hope right now you got the idea that how the
2:52
payment gateway and the payment processor actually differs among themsel. So here in a simple word a
2:58
payment gateway is a traffic controller of the payments whereas a payment processor is the system that actually
3:05
moves the money. Clear? Now now since you got the idea of what is a payment
3:10
gateway and the payment processor now let's start with the first step of our designing and that is the gathering of
3:17
the functional requirement. But before that I just want to tell you since designing of this payment gateway is
3:24
very much domaincentric means until and unless you do not have a thorough knowledge of the payment you cannot
3:30
basically design this system. So in general do not expect this question during your interview because in most of
3:36
the cases it is not expected that a candidate who is not from a payment background will know all these things.
3:43
But in case you face it, obviously you do not have any other way than to solve this problem. So let's start with this
Gathering Functional/NonFunctional Requirement
3:50
design. So the first and the foremost thing that we will be doing and that is the gathering of the function
3:55
requirement. So the first and the foremost requirement that we have to fulfill over here is number one the
4:02
client should be able to make a payment intent in our system. So as I already told you since this thing is totally a
4:09
domain related thing obviously the requirement will be also a domaincentric
4:14
it won't be a simple non-technical functional requirement that we have done in our previous video rather it will be
4:20
a very much technical functional requirement that we have to solve and one more thing I am also not from a
4:26
payment background I have to do a thorough research on this topic for the last one or two week and thereafter I
4:33
have came up with this designing it might happen that I will miss some of the point or some of the flow over here
4:39
but more or less I have covered in detail and it is sufficient enough to
4:44
clear any technical interview and if I have forgot to mention any of the point
4:49
or mention any flow feel free to let me know in the comment section so let's start with the first requirement and
4:55
that is client should be able to make a payment intent request number two the gateway environment that is what we are
5:03
developing should create a temporary session page by which the user will be giving the card details. So as you know
5:10
when we do a payment when we click on buy now there is a page that gets reload
5:15
or there is a page that comes up in the website where you have to give all the card details and everything for example
5:21
you have to select the credit card and based on that you have to give the credit card number CV and all those
5:27
details. So that is actually a page that is given by the payment gateway. It is
5:32
not that Amazon or Flipkart is creating that page. So this is a page that we
5:38
have to develop and we have to give to our client so that the user of that
5:43
client can enter the card credentials. Clear? Number three, we have to securely
5:48
handle the PCI complaints data. Now what is a PCI complaint? Let me tell you that
5:54
too. So a PCIDSS data is a global security standard for all the entities
6:00
that stores process or transmit the card holder data or the sensitive authentication data. So obviously
6:07
whenever you are giving the card details into a particular website as I was discussing earlier there after capturing
6:14
all those information there is a secure protocol that we have to follow or there
6:20
are some PCI standard that we have to follow so that we can save that information in our database and also we
6:27
can move forward to the payment processor and that is why here we have to maintain a secure ecosystem so that
6:35
the PCL standard is maintained. So securing the transaction is very much critical in this payment ecosystem.
6:42
Number four, once the transaction is done or it is successful, we should be able to give the transaction status to
6:49
our client. Clear? So these are the four most important functional requirement
6:54
that we will be solving over here. So as I was discussing these are the four
7:00
functional requirement that we have to solve for the payment gateway. I hope this is clear that what are the use case
7:06
or what are the functional requirement we are trying to solve over here. Now one more thing I want to tell you that
7:13
there are few of the things that we are taking out of scope. Number one a part payment. Number two the refund or the
7:20
return of the payment. So I will just mention it as the out of scope over here. And that's it. These are all the
7:26
functional requirement that we have to solve in this problem. Now since you have understood that what are the
7:31
functional requirement we are going to solve over here and you are somehow clear with what is a PCI data and what
7:38
is this temporary session thing now let's go to the next step and that is the gathering of the non-functional
7:44
requirement but believe me if you are not clear till now that what all these things are do not worry at the end of
7:50
this video you will be 100% clear with what each and everything meant and what you actually need to solve this problem
7:57
now let's go to the next part and that is the gathering of the non-functional requirement. So as you know the first
8:03
non-functional requirement that we have to solve is we have to get the estimation that what is the scale of the
8:09
system for which we are designing the system. So here if you ask your interviewer that what is the scale of
8:15
the system he will be telling that we will be handling a 10,000 request per
8:20
second. So that is the 10k TPS over here means that is the 10,000 transaction per
8:26
second. So this is the scale that we are targeting. So obviously since it is a gateway which is communicating with
8:33
multiple processor. So obviously the volume of the data will be quite huge. Number two the most important that is
8:40
the cap theorem. And as you know the cap theorem tells that whenever you are creating a distributed system you either
8:47
have to compromise between the availability or the consistency of the system. A particular module of the
8:53
system cannot be highly consistent or highly available at the same time. But
8:59
here in case of the payment gateway as you all know our system should be highly
9:05
highly consistent because here we are dealing with the payment transaction. It does not mean your system should be down
9:11
for some time but it should not get the priority over consistency. So here you can see I have given the priority of the
9:18
consistency more than the availability. Now the next important thing is like the latency of the system and whenever you
9:24
are talking about the latency of a payment gateway the latency should be as
9:29
nominal as possible and whenever we are telling that as nominal means we have to quantify it and so here what we will do
9:37
we will tell that our transaction should get completed within 200 millisecond. So
9:42
that is the amount of latency that we are targeting over here. So here if you just look carefully I have mentioned it
9:49
clearly that it should be below 200 millisecond response time for the payment authorization that is because I
9:56
have already told you a payment gateway does not do the transaction with the bank. So whatever our responsibility
10:03
that is the tokenization and the authentication that we should complete it within 200 millisecond. Thereafter we
10:10
will orchestrate that token to our downstream that is to the processor and it will take its own time but the logic
10:17
of tokenization and validation should be done within this 200 millisecond. Clear?
10:23
Now comes the last and the main thing and that is the security of the system and whenever I'm telling security it
10:30
means that our system should be a PCI DSS complaint system. Clear? So these
10:35
are almost all the non-functional requirement that we have to solve for this problem statement. So here if you
10:42
look carefully we have almost gathered all the functional and the non-functional requirement that we have
10:48
to solve over here. I know it is quite a highle requirement right now and you might not be familiar with all the use
10:54
case but as I've already told you do not worry you will get to know very soon. Now let's go to our second step of our
Entity Creation
11:01
designing and that is the identification of the core entity. So let's first identify that what are the core entities
11:08
that we can assume or we can identify as of now just by reading all the
11:13
functional require. So here if you look carefully these are all the code entities that we can find out over here.
11:20
Let's go through this one by one. So the first one is the merchant or the client. So here with respect to our system let's
11:27
first understand that what is a merchant or a client. So for example we have created a payment gateway and for us the
11:34
client is nothing but [clears throat] the business who have integrated us means the Amazon, Flipkart, Walmart or
11:40
whatsoever online platform who is doing the business that is nothing but our merchant or our client. The next core
11:48
entity is the transaction means the actual payments that is happening by our system. Number three the payment method.
11:54
Why payment method is important? So obviously whenever a user is doing a payment he or she have to select that
12:01
whether he have to do it with the help of a visa card whether he is using a master card. So the payment method is
12:08
important over here and that is why this will become our core entity. Number four is very obvious that is the user of the
12:15
customer which is nothing but the users of this merchant and the client who is actually giving the payment details.
12:21
Number five is the web hook. Means whenever you are making a transaction, you will be seeing that once you are
12:28
done with the payment, the payment page actually loads and comes to the failure or the success page. That is nothing but
12:35
a call back that gets generated when you submit some event to the payment gateway. And that is why this web hook
12:42
is necessary by which we will be giving our client the success or the failure
12:47
message from our system. Clear? And the last but not the least is the payment session. And in this system a session
12:55
for the payment is very very critical because whatever happens for a
13:00
particular transaction depends on the session. If your session gets invalidated or we cannot authenticate
13:07
your session with the payment that you are making, your payment will definitely get failed. So the session management of
13:15
this ecosystem is very very critical. So this will be another core entities for
13:20
our system. I hope you are clear with that what are the core entities that we
13:25
have identified as of now. It might happen and it will happen that there will be few more entities that you will
13:32
come across at the future but as of now just by reading this function requirement these are more or less all
13:38
the core entities that we have to list out. Clear? Now let's go to the third step of our designing and that is the
API Creation
13:46
API design. Now before going into the API designing I have to tell you few of
13:51
the other things because obviously I assume that you are not familiar with the payment ecosystem and you do not
13:57
have any prior knowledge that how a particular transaction takes place when you click on buy now. That is why
14:03
obviously it is impossible for you to develop that what are the relevant API
14:09
endpoints that you have to list down over here. So before going into the API designing what I will do I will just
14:15
give you a small idea that what are the steps that are actually involved when
14:21
you initiate a payment because without knowing that it is impossible to design the APIs. So let's first understand that
14:28
what actually happens when you click on the buy now. So what actually happens is like whenever you click on buy now a
14:36
payment intent get generated in the system. Means for example here we are
14:41
having two thing number one this is our client which is nothing but our Amazon or the flip card and let's take an
14:47
example this is our ecosystem that is the payment gateway now what happens
14:53
once a user clicks on buy now a payment intent request first comes to this
14:58
payment gateway means a buyer wants to make a payment. So this will be our first step called as the payment intent.
15:06
Now once the payment gateway pay means the system that we are developing once we receive a payment intent from our
15:14
client what we actually do or what we have to do we have to save this
15:19
information in our back end means a user want to make a payment and in the response what we will do we will send a
15:26
payment intent ID to the client clear so in the response of this API call we are
15:32
giving a payment intent ID so what happens is Like whenever we get a
15:38
payment intent from the client, the first thing what we do, we save all this information what is the item that he
15:45
want to purchase or what is the price of the item and all this information in our local database and in return to that we
15:52
send a payment intent ID in the response and once the client receive this payment
15:59
intent ID what they have to do it have to first secure the session means a
16:05
payment is going to happen. So from now create a session by which this entire
16:10
payment transaction should happen. So another request will come from the client to our payment gateway and that
16:17
is for the generation of a session means here what the client is telling that the
16:23
user want to make a payment and that is why create a session or create an environment for the user by which the
16:30
user can be able to make the transaction with the bank. So here the second request will be the session management
16:36
or the payment session. So these are the first two step that will happen with the client and the payment gateway. Now once
16:44
we see that the client want to secure a session or want to establish a session
16:49
request over here what we have to do in the request or in the call back we will
16:55
give a session or a temporary web page to the client which actually looks like a page where you can fulfill all your
17:03
bank credentials. So as you know once you click on buy now after a millisecond or so you land on a page where all the
17:11
card details appear where you can put all the card credential and everything and that web page is actually created by
17:18
this payment gateway and that have a session timeout means if the session timeout expire you will not be able to
17:26
fulfill the payment. So as you know whenever you are trying to buy something you will see that at the corner or
17:31
somewhere you will be seeing a stopwatch that is going on that is nothing but the timeout of that session. Clear? So once
17:38
the client makes a request for the session what we have to do in the return from the payment gateway we will give an
17:45
HTML page or a front end where the user can enter all the required credential.
17:51
Clear? Now once the user enters all the credentials of the card what it does it
17:57
clicks on the pay now that is the final step of the payment and at that time a
18:03
pay request come to the payment gateway is all the credential of the card is given by the user now it is the
18:09
responsibility of the payment gateway to tokenize it to manage it and pass it to the processor by some method. So these
18:16
are actually the three steps that are involved when you actually make a
18:22
payment transaction. I hope right now you are clear with what are the three steps that are involved when you are
18:28
making a payment and these are the three main end point that you have to expose
18:33
for your client so that the payment can be made successfully. So let's now list down all the API endpoints that you need
18:40
to fulfill all our functional requirement. So here you can see I have listed down all the endpoints or the API
18:46
rest endpoint that are needed to fulfill our function requirement that is the generation of the payment intent the
18:53
generation of the payment session and the actual request to make the payment and the last but not the least you can
18:58
see here we have taken a function requirement that is that is our platform should facilitate the transaction
19:04
tracking system means whatever the transaction that had happened we should be able to show the status of the
19:09
transaction and that is why here this is a get request I hope it is clear that what are the API endpoints that we have
19:16
to design over here. Now since we have almost completed the three major step that is the gathering of the function
19:23
and the non-functional requirement, the identification of the core entity and the API designing. Let's now go into the
19:30
next step of our designing and that is the highle designing of our system where
19:35
we will list down all the major components that are needed to fulfill all this functional requirement. So
19:41
let's go to the fourth step of our designing that is the highle designing of the payment gateway. So the highle
High Level Design
19:47
designing of the payment gateway is actually quite simple if you have understood the things that I have told
19:53
earlier that is how the actual payments happens over here. So let's draw it one
19:58
by one so that it will be easy for you to understand. So the first and the foremost thing that we have to introduce
20:04
are the clients for our system who are nothing but the big organization or the merchant who are actually making the
20:10
payment. So here we will be having our first component and that is the client or the merchant. I hope this is clear
20:17
and obviously this client and merchant should be also interacting with the user. So which is obviously not our part
20:24
of the designing but we will just mention it that there are few users who are actually dealing with this client or
20:30
with this merchant because they are the actual entity who will be giving the card details. So here there will be some
20:37
flows from the user to the client or the merchant. I hope this is clear as of now. Now here since we are creating a
20:44
system which support 10,000 transaction per second and we have different functionality of tokenization and
20:51
everything to fulfill. So obviously our back end should follow the micros service architecture clear and whenever
20:56
we are going with a microser architecture obviously we need a load balancer and API gateway to route our
21:03
traffic uniformly and that is why here we will be introducing our second component and that is the API gateway
21:09
and the load balancer. I hope this is clear as of now. This is quite a straightforward approach. Now starts the
21:16
main thing that is how the transaction will happen. So as I was discussing while doing the API designing what
21:23
happens at the first step of our transaction that is once the user clicks on buy now a payment intent request
21:31
comes to our server that is from this merchant or the client a request will be
21:36
coming into our server called as a payment intent request. And obviously to
21:41
handle the payment request we need a micros service over here. And that is why here we will be introducing a
21:48
service called as the payment intent service. And what it actually does once
21:53
it receive the payment request is capture or store all the payment related metadata into our backend database. This
22:00
which is the item the user want to buy, what is the amount that need to be deducted, what is the currency and all
22:07
this metadata of the payment should be captured by this payment intent service.
22:12
Keep it in mind it is not capturing the card details. It is not the responsibility of the payment intent
22:18
service to get the card details or any sensitive data. So what we will do? We will be using a database over here to
22:25
capture all this data. So here we will be introducing a database. Maybe we can call this a payment intent. I hope this
22:33
is clear. And as I was telling you, once this payment intent is saved into our
22:38
database, what we do? We give a response to our client that is the payment intent
22:44
ID. And once the client or the merchant receive the payment intent ID, it makes
22:49
a second call into the gateway and that is for the creation of a session. So the
22:55
next call that comes to us is regarding the creation of the session which
23:01
involves a payment intent ID that it have given in the response as well as the transaction ID and all those things.
23:07
So here we will be introducing our next micros service and that is called a payment session service. Now once this
23:14
payment session service receive the request what it actually does in the back end it create a session for the
23:21
payment and in return it gives a secure web page to the client by which the user
23:28
can enter the cart credential. So what it does in the response to this request
23:34
it gives a secure checkout web page. Clear? I hope this is clear. So all the
23:39
details of the card should be entered by the user in the web page that we the payment gateway is sending. It is not
23:46
that this merchant will create his own web page and get all the card details because that will be a very insecure way
23:53
to get all the card details and if the client does it without doing that PCI complaint it will go into a very big
24:00
security concern. So what happens to gather all the card information we the payment gateway gives a web page in the
24:07
session management and once the user get that web page what they do they obviously put all the information of
24:14
their card detail and clicks on pay and once it clicks on the pay another
24:19
request comes to our API gateway that is a payment now need to be done with the
24:25
bank and thus what we do here we will introduce another service called as a
24:30
payment processor processor service and this payment processor service is actually involved in making the
24:37
transaction with the payment processor. So here what we will do here we will
24:42
introduce another service which is nothing but a external service called as a processor service which is actually
24:49
doing the transaction with the bank. So here what we are doing here with the help of a secure connection we are
24:56
calling the processor service and once this processor is done with the payment
25:01
with the bank it sends a response to this payment processor service that a payment order have been placed
25:08
successfully on the bank. Just to clear one thing the response that we are getting right now is not the final
25:15
confirmation that the payment was successful or not. It is just an acknowledgement that a request or the
25:22
payment order have been placed to the bank. So what actually happens whenever
25:27
we are making this call over here though we are making the transaction with the bank but the confirmation that we are
25:34
getting in the response is not the confirmation that the money got deducted. So in some of the scenario you
25:40
have seen that while we are making our transaction in the UI we sometimes see that our payment got failed but somehow
25:47
in the SMS we get that money got deducted in the bank. Similarly, it can also happen that once you click on pay,
25:54
the actual payment did not take place but the order got placed successfully with the message that the payment was
26:00
successful. But after a few days or after a few hours, you can see in the
26:05
order list that the your payment got declined and it will ask for another payment return. And this actual scenario
26:12
is done with the help of the reconciliation with the help of the payment processor and the payment
26:17
gateway that we have developed over here. I will explain all these things in detail when we will be going into our
26:25
next step that how we should handle all the scenario of the failure because obviously since these things are all
26:31
related to money we should be 100% secure and 100% confirmed that a payment
26:37
got success or failed. So to implement all these things there should be a strong reconciliation job that should
26:44
run in the back end to validate all the session ID intent ID payment ID and all those things and at the end of the day
26:50
or the end of the hour it will give the response that the payment was success or failed. So here if you look carefully
26:57
this is what the highle designing of the payment gateway looks like. So here if you see I have tried to cover more or
27:04
less all the core entities that are needed to make the payment but believe me this is actually not at all simple
27:12
the way it look like and this designing is not even 1% that what we will be
27:18
doing in our next step of our designing and that is the deep type of our designing where we will design in detail
27:26
of each and every component where we will see that how each and everything will secure the data how we should parse
27:32
the data, validate the data and how we should encrypt the data and how each and every component will interact. So
27:38
without wasting much time and since you got a brief understanding of how the transaction is done in our payment
27:45
gateway, let's move to our fifth step of our designing and that is the deep dive designing of the system. Before
Low Level Design (Deep Dive)
27:52
proceeding further, I just wanted to notify that I have created a very simple website over here so that you get all
27:59
the contents that I upload on the YouTube on a single platform. So here you can see there are lots of content on
28:06
the system designing on the low-level system designing. Similarly, here we have the complete graph playlist where
28:12
we have already 15 to 16 video over here as well as all the latest contents that
28:17
I'm uploading on the YouTube. I will keep on updating all those things in this website. This is a free website
28:23
that is hosted also in a free domain. So do not forget to bookmark this website so that it will be helpful for you to
28:30
find out all the relevant contents regarding your upcoming interview. So let's start with the deep dive design.
28:36
So the first thing that I will do I will copy this entire highle designing and I will paste it in our deep dive design.
28:43
And let's start with our first component of our system and that is the payment intent service. So till now this flow
28:51
will remain the same that is here we have the user and here we are having the merchant who have actually onboarded our
28:58
payment gateway and as you know since we are using the micros service architecture. So obviously we will be
29:03
having the API gateway and the load balancer at the very beginning which have the general responsibility like
29:08
authentication and authorization routing of the traffic and load balancing. So all those flow will remain the same as
29:14
we have discussed in our earlier video. Now let's go into the first component and that is the payment intent service.
29:21
So as we have already discussed what the responsibility of this payment intent service that is once the user clicks on
29:28
buy now a payment request a payment intent request comes into our application and that request is being
29:35
handled by this payment intent service. Clear? Now as soon as this request comes
29:41
over here, we capture the metadata in our payment intent DB. Now let's see
29:46
what type of database we should choose and what will be the schema structure over here. So as you already know since
29:53
we are dealing with the payments and we have already told that our system should be highly consistent rather than
29:59
availability. So obviously we will be going with a consistent database and whenever we are telling a consistent
30:06
database means we should go with the relational database and whenever we are telling about the relational database it
30:12
should be a posgress solution or it should be a MySQL solution. So here we will be going with the Postgress
30:18
solution and let me show you how the schema structure will look like. So this will be more or less the schema
30:24
structure of the payment intent DB. So let's first check it out. So here what we are doing here once the request is
30:30
coming from our client or from our merchant we are creating a payment intent ID. This is an autogenerated ID
30:37
that we are creating in our system. After that we are capturing the amount currency the merchant ID the the
30:43
customer ID the order ID the payment method type and all those things. So there will be plenty more metadata that
30:50
we have to capture right now to validate the order in our later phase of the design. So these are more or less all
30:56
the data that we need to capture over here. And once we have created an entry
31:01
for our payment intent, what we will do here in the response of this request, we
31:07
will simply return this payment intent ID. Clear? So I'll just write it over
31:12
here that the response for this request will be the payment intent ID that we
31:18
are generating in this request. And that's it. This is the only thing that you have to describe for the payment
31:24
intent service. Clear? Now once the user or the merchant receive this payment
31:29
intent ID, what is the next step? We have to create a session or create a environment by which the payment can be
31:36
made. So the next request or the next API endpoint that gets called is nothing but the request to create a session. So
31:44
here if you have seen we have blackbox this entire implementation over here in our highle design. But here in this deep
31:51
dive designing we will see each and every component that is required to create this checkout web page or how we
31:57
will do all these things. So what I will do I will just get rid of this service and I will rename it to something
32:04
meaningful. So I will name it as a checkout session service means it is creating a session for our checkout
32:10
page. Clear? [clears throat] So the request is coming into our checkout session service. Now what is happening
32:16
here? From this service we have to return a web page for our front end. And
32:21
how we actually do it? The first thing that we do is we submit or we save this
32:27
information into some storage unit. So actually what we do once we receive the
32:32
payment intent ID in our previous call in the second call that is in our
32:37
session creation service there also we send the payment intent ID in the request as well as we send all the other
32:45
metadata like the transaction ID, the user ID, the order ID and all the meaningful data into our system. And
32:53
what we do since here we are initiating a payment from the payment gateway side.
32:58
So we first create or capture all this data in our database. And here if you
33:04
look carefully or understand the system carefully all the session that we are
33:09
creating for a particular payment is a very shortlived process means a particular session will be maximum to
33:16
maximum active for 10 minutes. So here instead of saving this information into
33:21
a database what we do here we use a radius cache to store all this
33:27
information and one more benefit of doing that is like the retrieval time of
33:32
this information will be very quick since it is a caching system and one more thing why we are storing all this
33:39
information in a radius cache is because here if you look carefully we have told
33:44
that the latency of this system should be as nominal as possible and it is only
33:50
possible when we omit the database access and we take the advantage of the
33:55
radius cache and all this caching mechanism. So what we will do first the first and the foremost thing once a
34:02
request come into this checkout session service all those metadata that are coming into this request we will simply
34:09
store it into our radius cluster. Clear? So here we will be having radius cache
34:14
and here we will save all the information and once we are done with this operation of writing into the
34:20
radius cluster what we will do in the response of this request we have to give
34:25
a web page to the client. Now obviously we are not giving a complete web page rather what we will do we will give a
34:33
generated URL of the web page means our payment gateway web page where all the
34:39
credentials of the debit card and the credit card will be inserted by the user. So let me just tell you how it is
34:45
done after that it will be cleared to you. So what we will do here if you look carefully this is how the response of
34:52
this checkout session service will look like. So here we will be returning a session ID which we are creating over
34:58
here as well as we will be giving a web page or a redirected URL of that web
35:04
page. So how it will look like? So for example, it is a premium gateway domain ID followed by the session ID for which
35:10
this response have been generated. So for example, there is a request that came into our session creation service.
35:16
Now what we are doing we are saving all the information in the radius cluster as well as we are generating a session ID
35:23
for that request. For example, this is your session ID and once we have generated the session ID in the response
35:29
to this request, we are creating a redirect URL of a particular web page
35:34
which also belongs to us. But the URL of that web page will look something like this. So this is our URL followed by the
35:41
session ID that we have generated over here. So this is how the response will look like. Now the next question is
35:48
obviously why we are sending the session ID as a parameter. This is totally because of the future authentication of
35:54
the system. So for example a particular client change this session ID over here. So at that time once the next request of
36:01
the pay comes into our system we will first validate that the pay request whether it matches with the session ID
36:08
that we have kept in our radius or not. And if it doesn't match we will invalidate that request and if it
36:15
matches then we will proceed with the payment activity. So here to validate that or to validate a particular request
36:22
we are sending the session ID in the parameter. Clear? So this is how the
36:28
response for the checkout session service will look like. Now once the user received this URL what they will do
36:36
since this is a redirect call. So obviously the client or the merchant
36:41
have to redirect their web page into this URL. And that is why from now if you just do a payment in any of the
36:47
website you will see that once you click on buy now there will be a small refresh that happens and thereafter the enter
36:54
URL on your search bar changes and then after you land on a payment gateway
37:00
where you can put down all your credential of the credit card. So this is how this is done. Now who will create
37:06
this web page? Obviously we have to do it. So here what we have to do we have to create a client side service which
37:13
will actually give them the web page. So let me tell you what I actually meant to say. So here we have to introduce one
37:21
more service that is called the checkout front end service which actually creates the HTML page for this following URL.
37:29
Clear? So here we will be having our next service called as checkout front end service. So once the client or the
37:36
merchant actually hits this URL the actual secure web page where the credential can be given is hosted in
37:43
this service. So from this checkout service the request will be coming into
37:48
our front-end service. Now if you look carefully we have taken an assumption that is the scale of the system is
37:55
10,000 request per second means 10,000 request is coming into our checkout
38:01
payment service for the creation of the session. Now as the request is coming we
38:06
are giving in the response the redirect URL. So obviously all the front end or all the client will receive this
38:13
redirect URL and we'll try to open that web page. So here the checkout front end
38:18
service will also receive those many amount of requests that is 10,000 request per second. So here also instead
38:26
of directly hitting this service we have to redirect all this traffic with the help of the load balancer. So what I
38:33
will do I will simply create another load balancer which will help to route all our traffic into our checkout
38:39
frontend service. So this will be another load balancer. Now the question might comes that why we are not passing
38:46
the same request from this API gateway or the load balancer that is because this is a single request that is here we
38:53
do not need a API gateway here it is not a API connection it is simply a front- end ecosystem or a front- end web page
39:00
that we have to display and we are having a single server with multiple replication and that is why here we do
39:07
not need an API gateway rather a simple load balancer will be doing and that is why here we are showing it in the
39:14
different boxes. So I hope it is clear that how the second step is going to complete. Clear? Now once the user puts
39:21
all the details of the credit card and debit card and click on pay. Now comes
39:27
the main thing that is we are going into the third step and the final step of the
39:32
payment when it will hit our actual checkout processor. So the third step
39:37
begins from here that the client have entered all the credentials of the credit card and they have clicked on pay
39:44
and once the client have clicked on pay the request will go into our payment
39:50
processor service. But here also instead of naming it as a payment processor service I will name it something
39:57
different and that is the checkout backend service because this service will actually handle whatever the data
40:04
that we have sent from the front end of this checkout service. So here what I will do I'll simply rename it as a
40:11
checkout backend service. So the client have clicked on pay. Now all the
40:16
metadata of the credit card and all the sensitive information of the credit card and all the PCI data have landed into
40:23
our checkout backend service. So here if you have understand this architecture clearly you will get to know one thing
40:30
that at nowhere the client or the merchant are having the access of credit
40:35
card or the debit card because here at all time whenever user have given the
40:40
information of the credit or the debit card it was within our environment because here they are using our HTML
40:47
page where they are inserting the data and here also they are submitting the data into our backend service. So by
40:53
nowhere this front end that is the client or the merchant can get the sensitive data of the user. Now let's
41:00
see what are the major responsibility of this checkout backend service because from here the actual system or the
41:08
actual drama start. So let's first see what are the responsibility of this
41:13
checkout backend service and how it will perform. So the main responsibility of this checkout payment service is we have
41:20
to first check that whether the session actually exist or not because it might can happen that some proster comes into
41:27
our system and try to do some hacking into our system. So we have to first check whether the request that had
41:34
landed into our backend service whether that request is a valid one or not. So
41:39
we have to first check whether the session exist or not. Number two, whether the session have expired or not.
41:46
So it might can happen that that the session was created but it got expired because as I already told you there will
41:52
be a session timer that keeps on running in our checkout page and that timer is
41:58
nothing but the TTL that you have set for this radius cache. Now I hope you
42:04
can correlate everything that how the backend system is developed. So obviously when you are inserting data
42:12
into this radius cluster obviously since it is a shortlived data so you have to
42:17
put a TTL in our back end and that TTL is nothing but a session of 10 minute
42:23
and that information of 10 minute is actually displayed on the web page that
42:28
we are showing to the user by this front-end checkout service. So obviously in the response of this checkout session
42:35
service we also have to send some other metadata like what is the time limit of the session and all those things. I hope
42:42
this is clear. So the TTL that we are sending from this check out session service is actually our indicator that
42:48
whether our session got expired or not. And after that we have to do one more thing and that is we also have to check
42:55
that the payment intent which we have received over here whether it is a valid
43:00
one or not. So from this shakeout backend service there will be multiple validation call that will go across our
43:07
system. So the first request will go into our radius cache for the validations. So as I already told you
43:15
radius cache will have all the information like what is the payment intent ID, what is the session ID, who
43:21
is the merchant, what is the order ID and all those information and if all those things matches with the session
43:28
request that we have received right now then only we can tell that the request
43:33
that we have received on the click of the pay is valid one. Clear? And if the
43:39
request is valid then we will go into our next step that is we will go in the
43:45
tokenization service. So obviously the data what we have received over here that is the sensitive data of the card
43:52
and everything which we cannot store into our system as well as we cannot transfer that data directly to some
43:59
external agent that is our processor service because it have to be a PCI DSS
44:05
complaint and this complaints or standard tells that we have to encrypt or tokenize this card details. So what
44:12
we will do here before making this processor call we have to make another
44:17
internal call and that is within our tokenization system which is itself a
44:23
secure and a PCI zone where all the tokenization is done. So let me first
44:28
draw that thing after that I will let you know how the things are actually working over here. So this is how the
44:34
tokenization system actually looks like. So let me just go through this one by one so that it will be clear to you that
44:40
how the things are working beneath the system. So what is actually happening once we have validated that a particular
44:47
request is valid and authorized. What we have to do? The first thing is we have to tokenize the card detail and for that
44:55
we are calling a particular service in our application that is called a tokenization service which is totally a
45:02
secure service or we can call it a PCI zone where all the credit card related
45:07
transaction or encryption actually takes place. So let's see what are the things that are there in this PCI zone. So the
45:15
first service that we are having over here is called as the tokenized service. So what this service is actually doing
45:22
the first one is like once is to receive the card number it first do a validation
45:27
that whether the card number is valid or not. Then if the card number is valid
45:33
thereafter what it does it generates a fingerprints for this card which comprises of the bin number the last
45:41
four digit of the card the expiration date and the name that is written on the card. So just combining all this
45:47
information and thereafter by producing a hash of it it actually creates a
45:53
fingerprint of that card so that in the future it cannot be decrypted if in case
45:58
it gets stolen. Now what is a BIN number? So if you just see the information that we have in a credit
46:04
card, so you will get to know that a credit card will be having a 16digit ID. And the first six characters that we
46:11
have is actually the BIN number which is nothing but the bank identification
46:16
number that whether the card belongs to ICA bank, whether it belongs to some different bank. So it is basically the
46:23
identification number the bank. So this first six number it actually captures
46:29
and then thereafter it takes the last four digit means this one 3 4 5 6 then
46:34
it takes the expiration date of the car and the name that is written on the car and just combining all these things and
46:42
creating a hash of it it basically create a fingerprint. Now once the fingerprint have been generated for a
46:49
particular card then we have to encrypt that card also and to encrypt a
46:54
particular card what we need we need a key for that encryption. So normally
47:00
what we do in a normal encryption way we keep the encryption key in some server
47:05
or some storage unit maybe a private key or a public key whatever it is we have
47:11
to store that key somewhere but in the case of the bank or in the case of the
47:16
credit card we do not have a private key or a public key to encrypt because
47:21
whatever you are storing in some cloud or in some storage unit that can be
47:26
stored. But to do this even more securely what we do we take the help of
47:33
a hardware service which is called as a HSM means hardware security module. So I
47:39
will just request you just check the Google that what is the hardware security model. So here you can see the
47:46
third step is like encrypting the PAN using the hardware security module. So here the pen does not means the what we
47:53
have or the Aadhaar or that identification number rather this is nothing but the card numbers or the
47:59
fingerprint that we have generated in our previous step. So here with the help of this three step here you can see we
48:06
are completely securing the data of the card so that we can thereafter transfer
48:13
that encrypted card details into some different system. So once there's validation of the card encryption and
48:20
everything is done what we do in the response to this request we send the
48:25
encrypted card token in the response. So the response of this service will be the
48:31
encrypted card token. I hope this is now clear that what we are actually doing
48:36
within this PCI zone and obviously one more important thing that you have to remember that this request is not a HTTP
48:44
request rather it is a TLS connection which is much more secure than our HTTP
48:50
or HTTPS solution. So this is how a particular card gets encrypted in a
48:57
payment gateway. Clear? Now once the card details get encrypted thereafter
49:02
comes the main thing that is we have to send this data to our payment processor.
49:08
Now what happens is like once this shakeout backend service receive this encrypted token ID it have to make the
49:16
final call and that is to the processor which can actually process the data with the bank. But before this also there is
49:23
one more important step that is by which processor the request should go. Whether
49:29
it should go with the rupees processor, whether you should go with the reser pay processor or whatsoever means who will
49:36
actually talk to the bank and how it is done. This is actually configured by the
49:41
merchant during the onboarding process. So here if you see here we are having the merchant and when they have
49:48
onboarded into our payment gateway service they have also registered one
49:53
more things that which processor they want to choose for their successful payment because the charge for a
49:59
particular transaction depends on the processor. So for example some processor takes 1% charge some takes 2% charge. So
50:07
based on those lines or based on some other data also this merchant or the
50:12
client will take the call that which processor they should talk to and for that based on the configuration that
50:19
they have set to diverse the request to that processor what we have to do here
50:24
we have to do something else that is once the checkout backend service receives this card token it will call a
50:30
simple service called as a orchestrator service. So here what I will do I will introduce a service called as a
50:37
orchestrator service and this orchestrator service will first shake the configuration of the merchant means
50:44
whether the merchant have chosen the pu processor or the result pay processor or based on that it have to divert the
50:50
traffic accordingly. So here what it will do the first thing is like this orchestration service will first talk to
50:56
a database that is nothing but merchant preference database. So here we will be having one more database called as the
51:03
merchant preference DB which will simply hold the information that for a particular merchant mean for example
51:10
Amazon will want to go with the reserve base system based on that the mapping object will be present in this merchant
51:16
preference team clear and based on that merchant preference what we have to do
51:22
we have to diverge the traffic accordingly means we have to call our processor accordingly and to do so what
51:29
we have to do we have to create our processor request and it is quite obvious that the request body of
51:36
different processor will be different and for that we have to go with a adapted design pattern. So let me just
51:42
draw that design pattern over here. After that I will let you know how the things are working over here. So here if
51:48
you see what is happening as the request comes to our orchestrator engine what it will do it will first check the
51:55
preference DB that is a merchant preference DB that which processor it will send the data and based on that
52:02
this orchestrator service will forward the data or forward that request to that following connector service. So here for
52:08
example this result pay connector service is only responsible to call the result pay system or the reser pay
52:14
processor. Similarly, the payu connector service is only responsible to call the payu processor. Clear? So, right now
52:21
what will happen? They will make the final call and that is to the processor who will be actually making the payment.
52:29
So, here we will be having some backend processor which are nothing but the finer payu and all those things and to
52:35
talk to this entire ecosystem what we have to do here will be a processor gateway by which we will be able to talk
52:43
to this backend processor. So here we will be having our next thing that is our processor gateway which is
52:49
completely an external agent. So until this point until this point this is our
52:55
system this is completely out of scope of our design. But I'm just telling you
53:00
that from here from this it will call the processor gateway and from this processor gateway it will internally
53:07
call the processor service that they have configured at the back end and this processor service will internally talk
53:14
to the bank for all the transaction that is doing clear. Let me just draw all the
53:19
things over here so that it will be easy for you to understand. So here this is our processor system which is an
53:26
external entity. Now if you look carefully we have already sent the request to the processor but we need a
53:33
confirmation from this processor that whether the payment was successful or not or the payment had happened to the
53:40
bank or not. So in the response of this request what it actually happens here we
53:46
have to introduce one more service which will be responsible to get the response from this processor. So I hope you
53:53
understand that here we are sending the request but since it is an external agent we cannot expect that on a zero
54:00
second we will get a response. So here we cannot get a response in this request
54:06
rather there is a call back function or a call back service that is responsible to get all the response of this request.
54:14
So for that here we have to create another service called as collector call back service. You can name it anything
54:20
you like. So here this is our service which is collector call back service which will receive all the response from
54:27
the processor service. Now obviously here there will be thousands and
54:32
thousands of request or response that it will receive and once we receive all the
54:38
status message what we have to do we have to obviously update the database
54:43
whether the spare request was success or fail. Clear? But here if you just look carefully I have missed one important
54:50
thing and that is here this orchestrator service before making the call to this
54:55
processors that we have over here it does one more thing and that is it saves
55:01
the information of the payment before going to the processor service. So here
55:07
we will be having one more database called as a payment transaction DB which is actually the core database where all
55:15
the transaction history or the transaction status are actually getting saved. So here we will be having our
55:22
main database called as a payment processor DB which will act as our persistent storage unit for all the
55:30
transaction that had happened through our gateway service. Clear? So here we will be having another database called
55:37
as a payment processor DBN and obviously this will be an RDBMS database and let's
55:43
see how the schema structure will look like. So this is how the schema structure of the payment processor will
55:48
look like. There will be thousands and thousands of other information also here but these are the most important thing
55:55
that we have to say that is the transaction ID, intent ID, status, amount, currency, merchant ID and all
56:01
those detail. Now as I was telling you once the request have been made to the processor unit and we get a response
56:09
into our callback service what we have to do based on the response we have to
56:14
actually update this database means here if you look carefully we have a field
56:19
called as a status means once the request have been sent by the orchestrator service into the processor
56:25
what it does it will mark this request as sent. Now once we receive our response from this processor service
56:32
into our call back service what we have to do we have to update this status
56:37
service and who will do it obviously it will be done by the single service and that is the orchestrator service. So
56:45
this orchestrator service have a major role in updating the status over here because if some other service update
56:52
this status service there can be a duplication or there can be a inconsistency within our database. So it
56:59
is the responsibility of this orchestrator service to update the status field over here that is the
57:05
request have been sent to the processor and the processor have given the response that the order have been placed
57:11
to the branch. So the status will be marked as done. Clear? So a particular
57:16
request that have come from the user have been placed successfully to the bank and right now we have a status
57:24
called as done. But now the question is how we will send this acknowledgement to
57:30
our front end that is nothing but our payment checkout front end which is
57:35
nothing but this web page that we have created for the user. Now let's see how
57:40
it is done. So this front-end service actually calls this checkout backend
57:46
service beneath the system. So it actually pulls the data for a particular
57:51
transaction request. So for example, once the user clicks on pay, it first sends the data to this backend service
57:58
and it keeps on polling for that particular request that whether the status of that request got changed or
58:05
not. If it got changed to success, it will show the user that it got successfully placed. Otherwise, it will
58:11
show it as failed. So this shake out backend service also have to do one more
58:17
thing that is here this shake out backend service have to see the status
58:22
of the particular request in this payment processor D to see whether the
58:27
status of this request have been changed to success or failed. Clear? So this is
58:33
how this entire processing unit or entire transaction actually takes place
58:38
in the bank. Now there is one more important thing [clears throat] that you have to know that is the request that we
58:44
have placed to the processor right now is not the final confirmation that the money got deducted from the bank or not.
58:51
It is just like the request have been placed to the bank. It might can happen that the transaction will get failed if
58:59
you do not have the sufficient balance or some other credential can also fail. And for that what we have to do there
59:07
should be a reconciliation job that will run after 1 day or 2 day which will
59:13
actually tally this transaction request with the response that is sent by the
59:18
processor. And based on that tally we have to confirm the client that the particular transaction got successfully
59:26
done in the back end. And that is why if you have seen that if a particular transaction fails on Amazon also if you
59:33
go and reach their customer service they will tell you that in case your money got deducted we will refund you or it
59:40
will get updated after 3 to 4 days. that 3 to 4 days is nothing but the
59:46
reconciliation time that it takes for all the data that we have collected to
59:51
validate and reconcile. And to implement that here what you have to do here if you look carefully I have intentionally
59:58
done one thing that is I have shown that this orchestrator service is directly talking to this call back service but
1:00:05
actually in real life it cannot be like that rather what we have to do here we
1:00:10
have to go with a eventdriven service means here once this call back service
1:00:16
receive the data of the status of a particular transaction it will put all
1:00:21
the status in a Kafka broker or in a particular buffer. So here I will put a
1:00:27
Kafka broker or introduce a Kafka broker and this Kafka broker will have few of the topics. So let me list down all the
1:00:34
topics that we have over here. So this Kafka broker will have two topics. Number one the payment processor call
1:00:41
back status means whatever the request we have sent to the processor all the
1:00:46
status will come immediately into this topic that is in the call back status
1:00:51
topic. Now once the data is there in this topic this collector service will
1:00:56
act as a consumer and instead of this reading it from this callback service it
1:01:02
will actually read from this Kafka topic. Clear? So here we can see we are
1:01:07
using a popsup design pattern means once the data is there in this topic this
1:01:13
orchestral service will simply read it from this Kafka and it will update the payment over here. Now after a day or so
1:01:20
once the final confirmation is done with the bank this processor service will again send an acknowledgement of each
1:01:28
and every transaction to this collector payment service and it will send it to
1:01:33
another topic called as a payment processor status which have the data of one day delay means it is not the
1:01:40
immediate data but the data which comes after one day and this status have the final confirmation that whether the
1:01:46
payment was successful or Now we have to do the final reconciliation and for that
1:01:52
what we have to do here we have to create one more service called as a reconcile service and this
1:01:59
reconciliation service will talk to this Kafka broker and will update the
1:02:04
database that we have over here that is the payment processor DB into some
1:02:09
different tables. It is not that it will update the same table rather it will be a separate ledger table which have the
1:02:16
final information of the payment mean who have done the payment what is the timestamp on which the payment was done
1:02:23
and all those information will be there on the last table of this entire ecosystem called as a payment table
1:02:30
clear so here if you look carefully I have almost covered everything that is
1:02:35
required to design a payment gateway ecosystem so I hope you have thoroughly
1:02:40
understood this video and you have found this video useful and I hope you have completely got the clear idea that how
1:02:47
each and every function are doing the validation, authorization, tokenization and how the data is getting PCI
1:02:53
complaint and how it is getting transferred from one service to another. And if you have understood it and if you
1:02:59
have found this video useful, do not forget to like, share and subscribe to my channel and hit the bell icon so that
1:03:05
you never miss an update from my channel and you are always ready for your next interview. So see you in our next video
1:03:12
where we'll be solving another problem from our system designing interview. So see you in our next video. Thank you.
1:03:22
[music]