Intro and Course Overview
0:00
If you want to understand what a service mesh is and learn one of its implementations,
0:06
Consul as well as understand why this concept is so popular in cloud and DevOps space.
0:11
And get your first hands on practice with it, then this crash course is exactly for you.
0:18
You definitely want to stick around till the end, because this is going to be a value packed, super exciting crash course with lots of interesting concepts.
0:26
First, we will see why we even need a service mesh technology like Consul and what it does exactly.
0:33
We'll then see its practical use cases, including how it's used in multi data center
0:39
and multi-cluster environments. We will understand Consul architecture so how it works
0:46
and how it does all that. And finally we'll see a really interesting demo use case
0:51
of deploying microservices application across two Kubernetes clusters on two different cloud platforms
0:59
and configuring the connectivity of these services across different environments using Consul.
1:06
And in case this sounds like complex topics and use cases, remember you are on Tech World with nano channel,
1:13
so you can be sure that I will break down all the complex topics into a simple and easy
1:19
to understand examples and explanations. So let's get into it.
Why we need a service mesh?
1:28
Let's say we have an e-commerce application like Amazon, which is a complex microservices application.
1:35
It has services for various functionalities like product catalog to manage product information, pricing,
1:42
product images, etcetera. We have a shopping cart service that allows adding products, removing them, maybe saving for later.
1:50
We also have order management service to handle all the orders. We have user authentication and authorization services,
1:58
obviously to manage the registration, user login and so on. You know, reviews and rating service,
2:03
recommendation service. And let's say it also integrates with bunch of supplier APIs and allows others to set up their
2:13
own shops or a payment gateway to integrate with external payment processors.
2:18
So a bunch of stuff is going on where this huge application logic is broken down
2:24
into microservices. And if you don't know what microservices are exactly
2:29
and how they are designed, I actually have a separate video on that which I will
2:34
link in here. And of course these microservices are interconnected. They need to talk to each other like when product is added
2:41
to shopping cart product service needs to update the stock information on how many products are left.
2:47
Shopping cart needs to talk to the payment service or user account. The user authentication service will talk to other
2:55
services that require user authentication like verify user identity, doing order placement,
3:01
or payment. For example, recommendation engine service will communicate with User authentication Service to personalize
3:10
recommendations based on user preferences, as well as talk to product catalog service to fetch product
3:17
details for recommended items. So as you see, it is a complex network of services that all need
3:24
to talk to each other without issues to make sure that the entire application works properly
3:30
and the user experience is smooth. And while moving from monolith to microservices,
3:36
architecture introduced a lot of flexibility in developing and scaling such complex applications.
3:43
One of the main challenges it introduced was the connectivity between those services.
3:49
In monolith application is just one application and one code base, so it's all function calls between different
3:56
parts of the application. But in microservices, you have multiple isolated micro applications,
4:03
which introduces a couple of questions and challenges like how do they talk to each other,
4:09
on which endpoints, what communication channel do they use? Do they send Http requests to each other?
4:16
Do they use message broker synchronous or asynchronous communication? What about the communication bottlenecks?
4:23
When one service is completely overwhelmed with requests from all other services?
4:30
How to deal with a situation where one service is down and not responsive to other services?
4:36
Like what happens if shopping cart service is down but other services depend on it to do their jobs
4:41
and it's just not responding? And how do we even monitor such application?
4:46
How do we know which services are up and running, which ones are having issues,
4:52
which services are overloaded with requests or not responding or just slow in their response?
4:59
So all of these are challenges that microservices infrastructure introduced.
5:04
Now let's say we have our microservice application deployed within a Kubernetes cluster in ECS
5:11
in one of the US regions. Let's say we are a US based company and we have mostly American users,
5:17
but we grow and become super popular in Europe and Asia. So now we need to deploy our application
5:24
in those regions as well, geographically closer to our new users,
5:29
to make their user experience better. So we need the instance of our application in other
5:36
geographic regions to make sure that our application loads fast and people in those regions have
5:43
good user experience. Now, this is another layer of complexity because now
5:49
the question is how do we manage communication between services across multiple regions,
5:54
in multiple data centers? That introduces a whole different level of challenges of operating your microservices application,
6:03
like networking and connectivity between those regions, making sure those connections are also secure,
6:09
making sure the data is in sync between regions and data centers. And you don't have data inconsistencies. Now,
6:18
as if that wasn't enough, our microservice is using two different databases
6:23
for different purposes, and those are managed centrally. By database engineers on separate VMs,
6:31
because let's say those databases are used and shared by the whole company. It's a legacy system.
6:38
Everything's interconnected. So it's not easy to move away from virtual machines
6:43
and migrate the database to a Kubernetes cluster. Let's say it's a large database with more powerful
6:51
machines and many replicas. So it would be an enormous effort to migrate all
6:57
that to a Kubernetes environment. So microservice application has to communicate
7:02
with database services running on virtual machines in on premise data centers. So we have a hybrid environment.
7:12
And that is even more challenging than managing connections between services on two
7:17
different Kubernetes clusters. However, it is a very common real use case among many
7:23
companies and projects. So that's a real challenge. Now our story continues.
7:28
Let's say one day right before the holidays, AWS has an outage in multiple regions around the world,
7:36
and we lose lots of business in our e-commerce application. So management decided to make sure this never happens again,
7:45
to have a failover to a different cloud provider, like a backup,
7:50
in case the main cloud provider has issues. So they replicate the entire application
7:56
on Google Kubernetes Engine, which is a Google's managed solution of Kubernetes,
8:01
because the chances of both and Google Cloud going down at the same time is very low.
8:08
And this is great for business in case of any such issues. But a new headache and challenges
8:15
for the engineers. Again, connectivity across multiple cloud providers now security,
8:21
network configuration and so on.
8:26
So as you see, the operations of microservices, especially in the modern,
8:32
highly complex environments is a challenge. And that's where the service mesh technology like Consul
8:40
comes in as the communication channel or communication network layer between microservices.
8:46
That solves many of the above challenges. Now that's a bit simplified definition of service mesh.
What is a Service Mesh? What is Consul?
8:52
But essentially service mesh like Consul, is the whole infrastructure layer that has different
8:58
features to solve these challenges of operating microservices applications and enabling
9:04
communication between them across multiple environments. Great. So now that we understand conceptually
9:10
what Consul is and why we even need a service mesh technology, let's actually understand how it works and how it solves these
9:19
challenges that I talked about. And the great thing is that most service mesh technologies
9:24
are pretty similar in their functionalities. So understanding the concepts of how Consul works will make it much easier for you to understand any other
9:34
service mesh technology as well. So I'm a big fan of concepts before technologies concept
9:40
to understand what problem you are solving and what is the need. And technology is then a tool for solving that problem
9:48
and fulfilling that need. So let's understand all that to understand the way
How it works without Consul - a K8s city
9:54
a service mesh like Consul works. Let's imagine we have a city with different buildings and roads,
10:00
and those apartment buildings have a bunch of residents in apartments, and those residents each do their tasks,
10:07
and sometimes they need information from other residents to complete those. So they send messages to each other to communicate.
10:15
And each resident has an own registry book, like an old address book with a list of all
10:22
the residents they talk to and their addresses, where they can send the messages. The city is the Kubernetes cluster,
10:29
buildings are the nodes, and the apartments are pods of each microservice,
10:36
while the residents are the service containers within the pods. And that phonebook is like a configuration file
10:42
for the applications in a container where they provide information of all service endpoints
10:47
with service name and port number. So basically where they have a list of all the services they talk to. Okay.
10:53
So that's what we are working with. No Consul no service mesh in our imaginary city yet.
10:59
Now let's see how our city residents or pods operate without a mesh.
11:05
If a resident moves to another building, all residents who were sending messages
11:11
to her need to now update their address book with the new address. Otherwise,
11:16
they will be sending the messages to the wrong address and wonder why they never get an answer back.
11:22
And this would happen when a microservice or database service gets a new endpoint or service
11:29
name or port changes. Now the city is managed centrally, like when someone is administering
11:35
Kubernetes cluster. So the administrators want all communication data going
11:42
through the services to be transparent and gathered in one place so they can identify if there are any
11:48
issues in the communication between the residents and fix those issues to see maybe how secure the city is,
11:55
how responsive the residents are to each other, and so on. So this residents need to keep a protocol
12:01
and report the city monitoring service about their communications. Each and every one of them needs to do that.
12:09
So making sure each resident does their job properly and consistently and while keeping
12:15
up with the messages, they do all these other administrative tasks as well, which is overwhelming for a lot of residents.
12:22
So they're working over time. I know this sounds like a weird city with surveillance system monitoring its residents
12:29
and making them work 24 over seven, but we are in a Kubernetes city, so it's fine.
12:34
And in Kubernetes cluster, this is equivalent to adding a monitoring endpoint in our
12:41
applications to expose metrics. So we can scrape and collect those metrics in Prometheus,
12:47
for example, or adding logic to each microservice for how to handle communication with other services
12:53
when they don't respond or when they get an error reply, like how do they retry the request, and so on.
13:00
And some residents might miss to track some data. Some of them will just track part of the data
13:06
and not all of it. They may all write in different formats or not readable handwriting's,
13:12
so the central service will not be able to fit those reports or that metadata about the communication
13:19
itself together, because they're all in different formats. So essentially anything related to communicate.
13:26
With other services, making sure the addresses and endpoints are up to date, proper handling of when they don't get
13:33
a response back or if there are any communication issues, and so on. The residents are responsible about all these themselves.
13:41
Now to optimize this city
How it works with Consul Service Mesh
13:47
and release some workload from our residents and let them focus on their main tasks. As city administrators,
13:55
we introduce a service mesh like Consul. Basically in every apartment for every resident,
14:01
we add a personal assistant. This assistants or agents are now saying to the resident,
14:08
I will send all those messages for you. In fact, you don't even need to know the exact addresses of other
14:16
residents that you are talking to. You just write their name on the envelope and I will find out where they live, and I will deliver the message.
14:24
And when they respond back, I will receive the incoming messages and forward
14:30
them to you. I will also keep a protocol of any information that goes through me. So all these administrative tasks around sending
14:38
the messages are taken care of by those agents or assistants,
14:43
and residents can focus on their main activities and the actual contents of the message.
14:49
In Consul this assistants are envoy sidecar proxy containers injected into the pod
14:57
of each service. As you know from Kubernetes, we have a service container running in Pod,
15:02
and we can run helper or sidecar containers that will run alongside to support that main service
15:10
container in its job. So these envoy proxies will act as those assistants living
15:16
in the pod along the service. And by the way, I have another video where I explain service
15:22
mesh with example of Istio. I explain the same concept but from a different angle,
15:28
so you can check it out as well. To get even better understanding and compare two different service mesh tools. Also,
15:35
if you are new to these concepts like running microservices applications in a complex
15:40
Kubernetes environment, I actually have a complete DevOps bootcamp where you can
15:46
learn all these with practical hands on projects as well as separate course focused specifically on microservices with mono repo,
15:56
poly repo structures, and building a CI CD pipeline for the microservice application on the git.
16:02
And in our latest program about DevSecOps, you can also learn the security focused
16:09
approach of working with containerized applications, Kubernetes cluster, automating security and compliance
16:15
checks for applications, and also learn about the production grade deployment of microservices application with a service
16:24
mesh in Kubernetes using the security best practices, along with tons of other concepts.
16:30
So if you are at the point where you want to take your engineering career to the next level,
16:35
definitely check out our courses and trainings to really dive in and learn these tools and practices properly.
16:42
And all these for a fraction of the price of what engineers with this skill set earn
16:48
in salary anywhere in the world. So how do these assistants do their job? Because now they need to have an address book and a way
16:57
to keep the protocol of things, instead of each resident having its own address book.
17:04
Assistants actually have a shared network with a shared address book,
17:09
so each assistant will add the information about their resident or their service and how to talk
17:16
to it in this central registry so other assistants can read that information as well.
17:23
So when a new pod gets scheduled with a new microservice, it will get assigned the assistant automatically.
17:30
So proxy will be automatically injected by service mesh and proxy will say to all the other
17:36
proxies or the shared network. Hey, we are new here. Me and my service.
17:41
And this is how you can contact me if you want to talk to the service that I'm assisting.
17:47
And I will then forward your message to the service. Now, when any service wants to talk to any
17:53
other service, they can say to their personal assistant. Hey, I want to send this request or message
18:01
to this service called payment. Please deliver it. The proxy looks at the shared registry to find
18:08
the location of the intended service based on its name or tags,
18:14
and it will send the message to the services address, where the agent or assistant of that service will open
18:21
the door and accept the message, and that agent will then deliver it to the actual service
18:27
inside the apartment or pod. So essentially that means services don't need to know
18:33
each other's endpoints at all. They have the assistance for that. So we free the individual services from having
18:40
to even know this information and extract it completely into the service mesh. And when we have new tenants in new apartments
18:48
and when old ones move out of the building or the city, agents update this information dynamically.
18:54
So instead of a static configuration file with endpoints, we have what's called a dynamic service registry
19:02
that is always kept up to date by those Consul agents. Now let's say a resident gets sick like they get
19:10
a burnout from too much work, in which case their assistant will update
19:16
the information in the registry and say my service is sick. They can't receive and reply to any messages for now,
19:25
and I will let you know when they're healthy and responsive again. So now if we have pod replicas of the same
19:32
service on same or different nodes represented by buildings,
19:38
other proxies will know to talk to one of the other healthy replicas of that service and not send the traffic
19:45
to the unhealthy replica by reading this health information from the shared registry.
19:52
And again, all of this is handled just between the assistance services.
19:57
Don't need to worry about handling any of this logic, or keeping up to date with which service
20:03
replicas are healthy or not, and trying to retrieve these health information from somewhere.
20:08
They're completely unaware of all this.
Secure Networking - How mTLS works
20:14
Now, let's say while agents are carrying these messages back and forth between services in different buildings,
20:21
some malicious actors like hackers managed to sneak into our city.
20:26
So they entered our Kubernetes cluster or our infrastructure and got access to our network somehow.
20:33
Now we have these malicious actors on the streets roaming around freely who want
20:38
to sniff these messages being sent between services, especially if they contain private,
20:44
sensitive data. Maybe they want to steal payment information or personal user data. Maybe they want to mess up the systems.
20:51
So if they snatch the envelope from the agents, open it and read it,
20:56
they will see all the information inside. So ideally we want to encrypt that communication
21:02
between the services. So even if hackers managed to get into our system and network and they were able
21:09
to see those messages, they can't understand anything because instead of plain text,
21:14
it's all encrypted and only our agents can decrypt them because they have the decryption keys.
21:21
So that's another feature. Service mesh offers encrypting end to end
21:26
communication between services using mutual TLS without mesh. If you had 20 microservices and you wanted to implement
21:35
encryption between them, you would have to change the application code in every single service to implement encrypting the data
21:43
or receiving encrypted data. Terminating encryption. You would have to implement the management
21:48
of the encryption keys and certificates to make sure that they are also securely created and stored.
21:55
And it's a lot of work on the development side. Again, that extra administrative work around secure
22:01
communication that has nothing to do with the business logic directly. Plus,
22:07
mostly these are the things that developers are probably not the most knowledgeable in and not
22:13
the best at implementing this stuff. You kind of need specialized knowledge to implement
22:19
this with proper security. So the fact that you get these out of the box in service mesh is pretty powerful. And this is interesting,
22:26
the microservice itself is still sending the traffic, which is unencrypted,
22:32
but before it leaves the apartment or pod, it's captured by the proxy.
22:37
The proxy has a TLS certificate with encryption key to encrypt the message.
22:43
So when the request leaves the pod, it's fully encrypted. When that encrypted request reaches the target
22:50
service or in Consul term, upstream dependency of that service,
22:55
that services proxy will then receive the message. And we'll do that TLS termination before
23:01
routing it to its host service, which basically means it will decrypt the message
23:07
with its encryption key and pass the plain text message to the microservice within the pod. So now,
23:14
even if someone infiltrates did Kubernetes network and was sniffing the traffic between the pods,
23:20
they won't be able to read the messages because they are all encrypted. And again, the microservices themselves have no idea that all
23:27
this encryption decryption is happening. From their perspective, they're just sending and receiving unencrypted messages.
23:33
The biggest advantage of service mesh is that all that functionality is built in the mesh itself,
23:39
which means it doesn't matter how your applications are programed or how other people's third party
23:44
applications are programed over which you anyways have no control. You can still use all these like end to end
23:51
encryption and error handling, etcetera with Consul without relying on the applications implementing this logic
23:58
or having support for TLS, for example. And that is super powerful and helpful when you're
24:05
operating complex, heterogeneous systems.
Zero-Trust Network - Authentication and Communication Rules
24:12
Now, these end to end encryption or mutual TLS between services gives us one more thing.
24:19
Since each service proxy gets its own individual certificate to establish secure connection with other services.
24:27
This individual certificate can also be used to uniquely identify the service and validate its identity. So,
24:35
for example, each resident or service gets their own unique stamp or certificate. So when they send the message,
24:44
the assistant stamps the envelope with the stamp or encrypts the message with their key.
24:50
So when the receiving agent or proxy gets the message, that agent can verify with the central registry,
24:58
is this stamp real or fake? Was it tampered with and which service
25:03
does it belong to? So we know this message really comes from the proxy of the payment service. For example,
25:10
since it's signed by its certificate, we can now use this information to define
25:16
rules about who can talk to who, like define whether payment service is allowed to talk
25:22
to user authentication service and frontend service is not allowed to talk to the database service,
25:27
for example. So after the identity is verified as a second step,
25:32
proxies will check the communication rules. So this is really a payment service sending
25:38
this message that's verified. But is it actually allowed to talk to my
25:43
user authentication service. So is this resident allowed to talk to my resident or does it maybe have a restraining
25:50
order if proxy sees oh, it's not supposed to be sending message to my service, then it can block the message and the connection
25:58
so it won't be forwarded to the service at all. If the rule allows it, then everything is verified,
26:04
so it will forward the decrypted message. This is also called micro network segmentation.
26:11
So instead of having a firewall on the security group level or a subnet level, we have firewall on an individual service level,
26:19
which gives us a more granular control of who can talk to our services on which ports. ET cetera.
26:26
That's why the term micro network segmentation. Now remember,
Observability
26:32
city wants to have protocols of who is talking to whom, especially when we limit those connections with strict rules.
26:38
We want to see who is trying to break the rules and talk to the services that they are not
26:44
supposed to be talking to, or generally which tenants are unhealthy maybe? Or who is sending and receiving? How much traffic?
26:52
Are there any bottlenecks in the system? What is the error rate and what error responses
26:57
are we getting from different services? Maybe a few services are getting too many requests
27:03
and are overloaded and on the verge of a burnout and proxies by being located exactly
27:10
in that traffic path where the data exchange is happening, automatically end up with rich telemetry data,
27:17
which they can then expose to an external system like Datadog or Prometheus.
27:22
And here's a great thing about proxies being the ones that collect and expose this data.
27:28
Consul proxies are all the same service, which is envoy proxy. So when they collect and expose the metrics
27:36
in different services, they all do it in the same way because it's the same application. So they collect and expose the same metrics in the same
27:43
format across all services. So it's easy to put together metrics of all services
27:49
and build unified dashboards from them in Prometheus and Grafana, which are the monitoring tools.
27:55
So this architecture gives us immense power to change and control things in the network
28:01
without having to do any changes in the applications, which means we are flexible to do whatever
28:08
we want very fast, and configure things very fast in a unified
28:14
way for all the services. Now you're probably thinking proxies have a shared
Consul Architecture - Consul Servers
28:20
address list of all other services. They have certificate data and they know who can
28:26
talk to who based on the rules configuration that they all share access to.
28:32
So the question is how do they get all this data? Or when a new proxy starts up,
28:38
who provides it with all this information? And where is this shared database and storage
28:45
of information and certificates? Where is it located? And that's where the Consul servers come in.
28:51
With our analogy. Imagine these assistants all worked for the same company,
28:57
and they had a headquarter office in the city in its own building, separate from the assistance.
29:03
This office is the Consul server. You can have a single room in a building,
29:09
like a single Consul server instance or a single pod replica. But if you are managing many services and their proxies,
29:17
you might need a bigger office. So maybe 3 or 5 Consul server pods.
29:23
So these Consul servers push out all the needed data to the proxies or Consul clients,
29:30
like service registry information, the configuration certificates. So we don't have to do anything to get certificates
29:38
in all this data to the proxies. All of this is done and managed automatically
29:43
by the Consul servers. So we have basically automated operations of the mesh itself.
29:50
And as I mentioned, those personal assistants have a network. They talk to each other exchanging
Consul Architecture - Control Plane and Data Plane
29:56
information and so on. And that network of personal assistants is called data plane.
30:01
And the central office or cluster of Consul servers
30:07
that manage these assistants network is called control plane. This means the data plane is managed centrally by Consul
30:14
servers or the control plane, so that they too can focus on doing their job
30:20
of handling the communication between services and if something changes or gets updated,
30:26
like the address of a service or new service gets added or removed, certificates get rotated,
30:32
they will get the update from the central office automatically. It's like these proxies are all working
30:38
for the same organization, having access to the centrally managed resources and data so they can all do their work easily.
30:46
And this control plane leaves separately, maybe in the same city, which would be the same Kubernetes cluster.
30:52
Or maybe they even have an office in a different city, which means you can spin up a dedicated Kubernetes
30:59
cluster just for the Consul control plane, and then connect it to the Kubernetes cluster
31:04
where the data plane is running. Now let's say we have
Consul in multi-cluster environment
31:11
multiple Kubernetes clusters with our microservices like in different geographic regions,
31:16
maybe replicated on different cloud platforms even. And this is like having allied cities or city allies where
31:24
cities form a network and decide, you know, let's form a partnership. So we will allow your services to talk to ours and vice versa.
31:33
In this case, you can have Consul control plane in each cluster. So own control plane office in each city.
31:40
Or again you may have one dedicated cluster or the main headquarter Consul control plane.
31:46
And it will manage all other clusters data planes from there which is a common setup.
31:53
This way you can avoid replicated offices and resources. For example in Consul is especially powerful
32:01
in such multi cluster multi data center environments. Connecting services across different environments
32:09
which can be a really big networking and security challenge if you're doing this without a service
32:14
mesh tool. So how does this happen with Consul? Think of Consul planting guards at the exit and entry
32:22
of the city in Kubernetes cluster. This guard is called a mesh gateway.
32:27
So if payment service from cluster one wants to talk to user authentication service in cluster two,
32:33
it will be the same process for the services where the payment service just says to its proxy, hey,
32:39
send this message to the user service, please. I don't know where it's running. Also, I don't care.
32:45
You will figure out how to deliver this message. Proxy will have the list of available services
32:51
provided by the Consul server, including services in all allied cities
32:57
where it says okay, this user authentication service lives in another city,
33:02
so it could hand the message over to the city guard. The guard will take it to the other cluster
33:08
and hand it over to the guard at the entry of that cluster, which is going to be the mesh gateway of the second cluster,
33:15
which will then deliver it to the proxy of the user service inside the cluster. And finally it will be forwarded to the user
33:23
service within the pod itself. And the response will flow the same way back to the payment service.
33:29
And we're going to see an example of this specific use case in the demo part,
33:34
where we will connect two Kubernetes clusters on two different cloud platforms with each other using Consul.
33:41
And the good thing is, it doesn't matter which cloud platform you use. It pretty much works the same all the time.
Consul in hybrid environment
33:47
Now when we talk about multi data center environments, it's not just Kubernetes cluster.
33:52
Many companies, especially large established companies, have tons of applications that run
33:58
on legacy systems directly on VMs. Or they have a large company wide database that database
34:04
engineers team is managing centrally that also run on VMs. And often that team already has a strong expertise of how
34:13
to manage and operate those services on the virtual machines. So the overhead of learning Kubernetes
34:19
and then learning how to migrate and operate the service on Kubernetes is often too large.
34:25
Or if it's a small legacy application, maybe the overhead is just not worth it. So these are real use cases where companies still have
34:33
services that will run on VMs and may not be migrated to Kubernetes or cloud anytime soon,
34:41
but these companies and projects still want to take advantage of the modern tools like Kubernetes and containers.
34:48
So the teams in that company deploy their microservices in Kubernetes cluster,
34:53
which now has to connect to the database on the VMs or connect with other legacy backends still running
35:01
on premise virtual machines. And if connecting multiple Kubernetes clusters is a challenge,
35:07
try throwing VMs in that mix that becomes even larger. Challenge of how do we connect those networks? And again,
35:15
service mesh tools make that easier by abstracting this low level network configuration
35:21
and letting you manage that on a service mesh level. What's great with Consul specifically
35:26
is that while other service mesh tools also have this capability, Consul actually treats the VM environment
35:33
with the same importance or as a first class citizen, same as the Kubernetes environment,
35:39
and doesn't treat it as an uninvited or undesired guest serving it just
35:45
because it's there and it has to. So how does Consul work on VMs? If we use our analogy again,
35:53
an on premise data center would be its own city with a bunch of private houses where each house is a VM,
36:01
the application or service will be the only resident in the house and the Consul proxy and.
36:08
Consul client will be living in that house along the resident, and we will have its own house for the Consul
36:16
server as main office. You will then configure the communication channel so that Consul server running on the VM can connect
36:24
to the Consul server in the Kubernetes cluster, so they can share information and create
36:29
connection channel for their residents. So now again you have Mesh gateway
36:36
in the Virtual Machine City as well. Who will communicate with Mesh Gateway in Kubernetes cluster.
36:43
This way it can connect to other allied cities like other VMs or Kubernetes clusters.
36:50
And once the trust and secure communication channel is established between them. Now the residents of both cities can talk to each other
36:59
through that secure channel. So again, now with payment service in Kubernetes, cluster wants to talk to the database on VM.
37:05
They go through the same exact process where payment just says to its proxy, hey,
37:11
send this message to a database please. Proxy will have the list of available services provided by the Consul server,
37:18
and it sees their database lives in another city. So through the mesh gateways the message will
37:25
get transported all the way to the database running on VM in a different data center. So as you see,
37:32
a service mesh like Consul is essentially the whole infrastructure layer that has different
37:38
features to solve these challenges of operating microservices applications and enabling
37:45
communication between them. So in this demo part we're
Demo Overview
37:52
going to create a Kubernetes cluster on AWS using ECS service.
37:58
So that's going to be our very first step. Once we have the Kubernetes cluster we're going
38:03
to deploy a microservices application with lots of services inside the cluster.
38:09
And we're going to use an open source microservices application project from Google.
38:15
So it's a little bit more realistic, like a more complex microservice. And not just two services for the demo.
38:22
And once we have that all set up, we're going to deploy Consul on ECS,
38:27
and we're going to see how the proxies will be injected in each one of those microservices. What configuration changes we're going to have to make
38:35
to the microservices Kubernetes manifest files in order for Consul to work in Kubernetes,
38:42
and also explore a couple of features of Consul and what it gives us out of the box.
38:48
Once we have all of that set up, we're going to create another Kubernetes cluster
38:54
on a different cloud platform. And we're going to use fairly simple Kubernetes managed
39:01
service on Linode Cloud platform. I like using because it's super simple
39:07
to spin up a cluster there to create it manually. It's just very little effort compared to ECS,
39:13
and it's also very fast. So we're going to use that as a demonstration for another Kubernetes cluster.
39:18
But it could really be any other Kubernetes cluster that you want. So the concepts are the same. And then in that linode Kubernetes managed cluster,
39:27
we're going to deploy the same exact microservice and same exact Consul configuration.
39:33
And once we have that we're going to connect those two clusters together using Consul. And we're going to see the demo of or simulation
39:42
of a service going down or crashing inside the cluster.
39:48
And it failing over to the same service inside the Elk cluster.
39:55
So basically a multi cluster environment with a service failover to another Kubernetes cluster.
40:03
So let's go ahead and do that step by step.
40:08
Where along the way I'm going to explain lots of different concepts related to Consul service mesh.
Create K8s cluster on AWS EKS
40:15
So the first step is we're going to create an EKS cluster. But of course we don't want to do that manually
40:23
because it's a lot of effort and it's not the easiest thing to do.
40:28
So we're going to use infrastructure as code using Terraform and all the code configuration files,
40:33
the Terraform script, the microservices application, all of that will be linked in the video description.
40:39
So you can clone those repositories and follow along. So this is one repository where I'm going to have all
40:47
my Kubernetes manifest files that we're going to use to configure Consul and deploy our microservices application.
40:54
So all of that is going to be here. And we have the Terraform folder inside
40:59
with the Terraform script for creating the EKS cluster. And I have this repository cloned locally
41:05
so that I can work on it using my code editor with terminal.
41:11
So this is where we're going to be doing most of the work of configuring stuff. And I also have my account ready where we're
41:18
going to be creating the Elastic Kubernetes Service.
41:23
Right now we don't have any. So let's create one. And before we do, let's actually go through a little bit of the Terraform
41:31
script and what we're doing here. It's pretty straightforward actually. I'm using the modules to make my job easier.
41:37
So I'm using the VPC module to create a new VPC for the EKS cluster.
41:43
Our EKS cluster will be publicly accessible. That's very important. And therefore we have the public subnet in addition
41:49
to the private subnet in our VPC. And then I'm just using the X module to create the cluster
41:57
obviously referencing this VPC. And we're basically configuring it with a bunch of parameters
42:04
to configure our cluster. So first of all as I said I want my Kubernetes cluster
42:09
to be accessible externally. So with this attribute we can actually create a public endpoint.
42:16
Or we can let create a public endpoint for our Kubernetes API server.
42:22
So we can connect to the cluster using kubectl for example or browser whatever from outside the VPC.
42:30
Right. So I'm setting this to true. To achieve that the next attribute
42:36
is adding some security group rules. And this is actually important for Consul
42:42
to be able to do its job. And there are some specific ports that we need to open
42:48
on the worker nodes themselves, where the Consul processes will be running in order to allow Consul components to talk
42:56
to each other, and for the Kubernetes control plane components to reach Consul processes as well.
43:02
And I'm actually going to reference to the list of ports that we need to open
43:08
for Consul. So you see what they are and why those ports are needed. However,
43:14
just to make things simpler and to make sure that you guys do not have any networking issues with Consul,
43:22
and just to make sure that things go smoothly, what I'm going to do is, as you see in the Terraform configuration itself,
43:29
I'm actually going to open all the ports on my worker nodes, and I want to stress that I'm actually doing it for the demo,
43:36
because the security best practice is to have only those ports open that you actually need exposed,
43:43
and only those internal or external processes that need access to whatever service is running
43:49
on that port needs to have access to that port and nothing else. However, this is a demonstration,
43:56
and I just want to make it easier for you guys to follow along and to make sure you don't have any networking problems when deploying Consul.
44:04
And finally, this is the managed node groups. So these are the actual worker nodes or the worker node group
44:10
configuration for the cluster. And here we're basically just choosing the small instances.
44:16
And we're going to have three nodes or three of those instances in the cluster. And finally we have these two configuration pieces
44:26
which are also needed for Consul deployment. So these are basically the configuration
44:31
for the dynamic volume configuration because Consul is a stateful application.
44:38
So it actually deploys a stateful set component and it needs to store and persist some data.
44:44
So it needs to create the volumes on whatever platform it gets deployed. And in this case,
44:50
we are making sure that creation of Amazon Elastic Block Storage is enabled
44:57
for the cluster by giving permission to processes on these nodes to create the storage. And in addition to this role,
45:07
we have to enable what's called an add on on EKS cluster, which allows for automatic provisioning of the storage.
45:15
And once the cluster is created, I'm actually going to show you all this information so we can see that visually as well. Apart from that,
45:21
we have variables that we are setting and I have added some default values for most
45:28
of the variables, so you don't have to set them in the TF vars file.
45:33
So these are basically just Cidr blocks for VPC private and public subnets. The Kubernetes version.
45:38
That's very important to make sure to choose the one of the latest ones. This is the latest one as of now.
45:45
So that's what I'm using the cluster name because we use that in a couple of places
45:51
within the main configuration. So I extracted that as a variable region. You can set whatever region is close to you.
45:58
And there are two pieces of information or variables that you have to set yourself to execute the script.
46:04
Everything else is configured and set already. So before you are able to execute this Terraform script,
46:10
make sure to go to your AWS account and for your user,
46:16
create an access key pair and you have to set those values for the Terraform. Object.
46:23
So I have defined them and referenced them right here in the provider configuration,
46:29
which means I can just set those variable values in my Terraform dot vars file, which I have done already.
46:37
And once you have that, you should be good to go and terraform. Tfrs is a simple text file with key value pairs.
46:44
So you have the key name, which is. This one equals whatever your key id is in quotes.
46:51
And same for the access key. So set those two values in the tf vars file and we are good to go.
46:58
That's the provider configuration. That's the version that I'm using. And now we can actually execute this Terraform
47:05
script to create the EKS cluster. So I'm going to switch to the Terraform folder and I'm
47:12
going to do terraform init. So terraform init basically downloads any providers
47:18
that are specified here just like you download dependencies of your code. For example in order to run your project.
47:25
As you see it creates this dot terraform folder where the modules and providers will be downloaded.
47:32
Those modules and this provider and everything is green, which means our Terraform has been initialized.
47:39
We also have the Terraform log file. And now. We can execute Terraform apply.
47:48
You can do Terraform plan for the preview. But I'm going to do terraform apply immediately.
47:54
And we have to pass in the variables file that defines any missing variables. So.
48:03
VAR file is terraform tf vars. And let's apply.
48:15
And this is our preview. All the things that will be created. I don't need to look through that.
48:20
I'm going to confirm, and this is going to take a couple of minutes to create everything,
48:26
because lots of components and things are being created. And once the cluster has been created and fully initialized,
48:34
we can continue from there. So the Terraform script
48:40
was executed and it took some time, but it successfully executed.
48:46
So now if I switch back to my AWS account in the region
48:52
that you have basically set in the variables file, I chose the EU central region, which is closest to me.
49:01
So this is my EKS cluster that was created in the Frankfurt region.
49:06
And if we go inside and check out the detailed view, I'm going to show you a couple of things that we have
49:14
configured in our Terraform script that we can see in the UI as well. So I want to point out a couple of configuration details.
49:21
First of all we have the cluster configuration details. So we have the role the IAM role for the cluster
49:29
which is this one right here, as well as security groups for the cluster like this.
49:35
And then we have the configuration details on the node groups or the worker nodes themselves.
49:41
So if I go to compute we're going to see the three nodes that were created because that is our configuration.
49:48
We have defined three nodes. So these are basically the work node instances
49:53
that are running in our account. So if we go to EC2 dashboard,
50:00
we're going to see these three instances here. And we have the security group configuration on the worker
50:08
node level, which is this one right here. And note that this security group additional rule
50:16
actually applies to the worker nodes. So this is the same security group that all the nodes share.
50:21
So it will be same for each worker node. And we have also configured this additional
50:27
policy for the IAM role which also applies
50:33
to the node groups. So now the cluster the EKS cluster role or the control plane role.
50:39
But the node group role that apply to the worker nodes. And again we can see that right here in
50:47
the instance configuration. This is the role. And we should see this Amazon EBS,
50:53
CSI driver policy listed here. And I'm pointing this out because first of all,
50:59
you need to understand that these two things are configured separately. You have the control plane configuration with EKS
51:06
which is actually running in its own network. And then you have the worker node configuration with its
51:12
own role on port's own firewall configuration and so on. So if you have any networking issues and so on,
51:18
this should help you troubleshoot and know where to look for things basically. And finally last thing I want to show you is these
51:27
EBS CSI driver. Add on that we activated on our cluster.
51:32
And you are going to see that in the evidence tab for the cluster.
51:39
And right here we have Amazon EBS CSI driver which basically is needed in order to automatically
51:48
provision the elastic block storage for persistent volumes inside the cluster.
51:54
So in our case Consul stateful set actually needs a persistent volume. So this allows the cluster to automatically
52:02
provision the Amazon block storage for those volumes. Awesome. So the cluster is already active.
52:09
So we can connect to it using kubectl and deploy our application inside.
Deploy Microservices App on EKS
52:19
So I'm going to switch back to my code editor. And I'm actually going to use the terminal here.
52:25
So we have everything in one place. And we don't need the Terraform script anymore because we executed the provisioning already.
52:33
So now the next step is to actually connect to our EKS cluster. And we do that using AWS command line interface.
52:40
So this is basically a secure way to retrieve a cube config file from the EKS cluster without exposing any
52:50
credentials and without having to download this kube config file, and so on using a simple command,
52:56
which means you have to have installed. If you don't, it's pretty easy. Just go ahead and install command line interface
53:04
on whatever operating system you have. And once you have that, you need to also configure your CLI to use the access keys,
53:14
which can be the same access keys that your Terraform is using for this demo use case,
53:19
because command line interface will need the access credentials to connect to the AWS account. Right?
53:27
And I have already configured all of that with AWS configure command.
53:33
So just make sure that the default region and credentials configured here are for the same
53:40
account as for Terraform, and you should be good to go. So. With that setup I'm going to execute AWS X command.
53:50
Update. Kube config. And you can actually provide the region here as well
53:57
for where the cluster is running. So central one and we are going to need
54:05
the cluster name as well. And we have that here we call the cluster.
54:11
This generic name. So I'm going to copy the cluster name. So basically what update kube config subcommand does
54:19
is it fetches the cube config file which is like a credentials file for Kubernetes cluster from AWS.
54:27
And it stores it locally into a default cube config location,
54:32
where cube CTL will look for it and the location is on your user's home directory in dot cube folder.
54:41
So after executing this command you should find cube config file in there. So let's execute.
54:47
And there you go. You see the output that the cube config was. Or the context of the cluster was added in this location
54:56
in dot cube slash config. So if you don't have the dot cube folder already,
55:02
it will basically create one and add the cube config file configuration in there. Or if you already have one,
55:08
it will just append to the existing config because you may be connected to multiple clusters.
55:14
So all of those configuration will be right here. That's how it works for Kubernetes in general.
55:19
So nothing is specific here. And that means we now should be able to connect
55:25
to the cluster using kubectl command. So let's see. Kubectl get node. And there you go.
55:33
We have our three work nodes with this Kubernetes version
55:38
which we have defined here. Awesome. The first step is done as a next step. We want to deploy microservices application
55:46
into this Kubernetes cluster. So for that I'm going to actually switch to the Kubernetes folder where I have my manifests.
55:56
And I'm going to close this up and expand this. So these are all the config files we're
56:01
going to need in this demo. But we're going to start with the simplest one. So that's all we need to deploy our microservices.
56:09
So actually we don't need the repository of the microservice application itself. We just need a reference to the images.
56:15
So this is a Kubernetes config file that references images of all those microservices.
56:21
But of course I'm going to link the microservices repository in the video description as well.
56:26
So this is an open source microservices demo repository from Google.
56:32
And all those images are public which makes it easy to use it for demos.
56:38
And this currently happens to be the latest version. If the version has changed, you can check in the provided link
56:45
and you can just update the version basically. So super simple actually, we just have a bunch of deployments for each service.
56:52
The configuration is pretty similar for each microservice. They just run on different ports and have different names.
56:59
All of them have cluster IP services which are basically internal services. And we have one entry point microservice,
57:08
which is the front end that will then route the traffic to all the other microservices.
57:14
And here we see basically the frontend talks to all other services, and it is the only one that has an external
57:22
service of type load balancer. And all those microservices also share a Redis
57:28
memory database. Again, pretty simple setup. Nothing crazy here. So that means once we apply this configuration file,
57:37
all the images will be downloaded, all the pods will be created, deployment services and so on.
57:43
And we're going to have one entry point service to the cluster through load balancer.
57:48
Now for simplicity I'm not going to deploy an ingress controller in the cluster. So we're just going to use the load balancer service
57:55
directly to access our application, which is going to be enough for our demo.
58:01
So let's go ahead and apply this config file.
58:09
Config dot Yaml. That's all we have to do. And by the way, there is one service that is misconfigured
58:16
slightly on purpose, which is a payment service. It basically is missing one environment variable.
58:21
So it's not going to be able to successfully start in a pod, but we're going to need that to demo that later
58:28
in Consul. So let's execute and see the result. And we have the output of all the stuff that was created.
58:36
So we have quite a few microservices here, and it will need a little bit of time.
58:41
And we're going to check kubectl get pod. So they will all be created in the default namespace.
58:48
So if we do kubectl get pod we should see all our pods are up and running except for the payment
58:55
service which is going to stay in the error state which is fine. We're going to use that as an example
59:02
of an error in microservice to see it in Consul. Okay. So that was pretty easy.
59:08
Now what we actually want to see what we deployed. So I'm going to do kubectl get services.
59:16
And as you see all our services are cluster IP type except for the frontend external.
59:23
That means if you have watched my other Kubernetes tutorials, you would know that load balancer external service
59:29
gets the internal cluster IP, but also the external IP because we need to be
59:35
able to access it externally. And this is the external domain name for the load
59:42
balancer that will then map to the external IP. So where does it come from. That's also pretty easy as it works in Kubernetes.
59:50
When you create a load balancer on whatever cloud platform, you are creating this load balancer service.
59:56
It will in the background use that Cloud Platforms load balancer service to create the native load balancer there.
1:00:04
So that's where the external IP comes from. And that means if I switch back to AWS and go
1:00:13
to EC2 service. That's where we have the load balancers.
1:00:18
We should see our load balancer for the front end external right here.
1:00:24
And this is basically the DNS name that we see right here right ending in 138 configured on Http port
1:00:34
forwarding to this port which is configured right here. So pretty simple.
1:00:40
We just grab this DNS or external DNS name. And since port 80 is the default Http port it will
1:00:48
just open it like this. And there you go. Our microservice is deployed.
Deploy Consul on EKS
1:00:55
Now the next step is to actually deploy Consul in our cluster and use Consul for our microservices.
1:01:02
So how do we deploy Consul. There are several ways to install Consul on Kubernetes cluster.
1:01:10
One of them is using Consul's Kubernetes CLI and another one is using Consuls.
1:01:16
Official helm chart for Kubernetes, which is what I'm going to use. So if we search for Consul,
1:01:23
helm, chart and open the installation guide on their official documentation, always try to refer to the official documentation
1:01:31
instead of some blog posts because they are most up to date. So for the latest version,
1:01:36
these are the instructions. We basically add the HashiCorp helm repository.
1:01:42
We install the Consul chart and provide any parameters we need.
1:01:49
And if you have watched my helm chart videos, you know that helm charts are configurable so we can
1:01:55
actually provide any parameters, any configuration options in order to configure
1:02:00
the service using those parameters. Right. So for example, with Consul service mesh I mentioned
1:02:06
it has multiple features. And depending on which features you actually need, you can enable them by configuring them
1:02:13
as the chart values or passing them as chart values, and to see what values are available
1:02:20
to be set and parameterized. Obviously we need to see the values yaml file.
1:02:25
So we have a chart reference here. So that's basically the chart values reference documentation.
1:02:32
I usually actually prefer the values stored file in the repository. So for example this one.
1:02:38
But as you see the repository has been archived. So this documentation is up to date and something
1:02:45
that you should reference. But even though it's an advantage to have the chart highly configurable so you can
1:02:52
actually tweak it to whatever desired configuration you have in mind. If you don't know what you're doing,
1:02:58
there's this huge list of values that you have to basically understand what they're doing.
1:03:04
And it's pretty difficult to understand all these configuration. So we're going to use a couple of these configuration options.
1:03:12
And I'm going to explain to you what they're actually doing. But if you need any additional configuration options you can find those listed here with descriptions.
1:03:20
I don't think it's the most comprehensive and understandable, but at least you have some reference point.
1:03:26
So let's switch back to the project. And I'm going to walk you through the values file that I have configured for our specific Consul installation.
1:03:38
Which is actually pretty simple configuration. We have this global attribute which applies to all
1:03:45
the components that are part of the chart. As you know, chart usually holds or is a bundle
1:03:50
of multiple components of different Kubernetes native components as well as custom resource definitions and so on.
1:03:57
So this applies to multiple components. First of all, we have the Consul image with the version.
1:04:04
We are enabling TLS communication between the components and services. And since we want to connect multiple clusters
1:04:12
or multi data center environments basically with each other, we are also enabling the peering.
1:04:19
Then we have the Consul server configuration. As I explained, the Consul server is the control plane
1:04:25
that manages all the proxies, the Consul client and so on. And usually in a production environment you want to have
1:04:32
at least three replicas, not just one, because if one replica dies, you want to have a failover.
1:04:37
In our case, we're just going to use one server for our demo purpose. So you can configure that here.
1:04:44
This is an important configuration option. Connect inject is basically the name, the technical term of the service mesh
1:04:51
functionality of Consul. And what this configures is basically
1:04:56
if we enable connect inject it will allow Consul to automatically inject the proxies,
1:05:04
those helper containers, as I mentioned, into the pods of services.
1:05:09
So that's what enabled true does. And then we have the second configuration that says default false which is actually
1:05:16
the default value. But I wanted to specifically configure this. So if this is set to false then you would need an extra
1:05:24
annotation inside the Kubernetes manifest files or deployment manifest files in order to actually
1:05:32
inject the proxy into that pod. If we set this to true as well,
1:05:37
like this, then it will actually inject those proxies, even if we don't have the Consul
1:05:44
annotations in the deployments. And this is a good thing to have control over,
1:05:50
because it could be that you have pods running in your cluster, that you don't want to have any proxy services in them,
1:05:57
or you need to, or maybe you have some namespaces that should not have any Consul proxies applied.
1:06:04
So if you set it to false, you basically decide per deployment per application
1:06:10
where you want the proxy injected. So I'm going to set it to true. So we can see how that works.
1:06:16
And we actually want all our services to have the proxy injected. And we don't want to add annotations one
1:06:23
by one on each deployment. So I'm going to set it to true.
1:06:28
And that's the connect inject configuration. Then we have mesh gateway,
1:06:34
which as I explained is basically a connector between multiple environments. So mesh gateway is like a guard that is standing at
1:06:42
the entry or exit of the city with our analogy. And you can also have multiple replicas of the mesh gateway,
1:06:49
because if one of them goes down or has an issue or maybe becomes a bottleneck because of the number
1:06:56
of requests, you can actually scale up the replicas. And again, it's a feature that you can enable if you actually need to.
1:07:03
So if you don't have a multi cluster environment or just for security purposes,
1:07:08
you need to stay within the cluster, then of course you want enable it.
1:07:14
And finally we have UI which gives us a Consul, dashboard or UI where we can see the services and where
1:07:22
we can even configure stuff which we are actually going to be using in our use case and type load
1:07:28
balancer basically means that it will create a service, an external load balancer type of service, so we can access the UI. And we are also enabling that.
1:07:37
So that's the configuration that we want to apply to Consul in our cluster to one,
1:07:43
or inject the proxies in our microservices pods. And second, allow us to connect to Kubernetes clusters
1:07:51
with each other and also have a dashboard where we can see stuff and configure some things.
1:07:57
So I'm going to go ahead and actually install the Consul helm chart with these values. And let's see what we get.
1:08:04
So I'm going to copy the first command and let's add HashiCorp repository. There you go.
1:08:11
And now we can actually install helm install. And we're going to give our Consul chart deployment a name.
1:08:18
You can call it whatever you want. I'm actually going to call this X to basically differentiate it later from the Linode
1:08:26
Kubernetes Engine deployment. So I'm going to go with that name. And then obviously we need the chart name.
1:08:33
I'm going to copy it from here. And actually when components are created it prepend Consul in the name.
1:08:38
So that's why I'm not using X Consul or Consul in the chart name itself. And I'm actually going to add some additional
1:08:45
parameters which can also be configured in the values. But I'm going to set them separately because I'm going
1:08:51
to use the same values file for the Consul deployment as well. So I'm going to pass in the version first of all.
1:08:59
And we're going to use. Version one. And then of course,
1:09:05
we have to pass the values file. Consul values dot yaml.
1:09:11
That's our file. And finally the last configuration is I'm going to set.
1:09:18
A global config. So one of those global attributes called data center.
1:09:27
And that's basically the name. So you can name the environment where Consul is running.
1:09:33
You can give it a name of a data center. And I'm also going to call this x. And that's basically it.
1:09:40
So I'm going to execute this command. And this should install all the Consul
1:09:46
components in our cluster. And this gets executed pretty quickly actually I'm
1:09:51
going to do kubectl get pod. So first of all I'm going to check the pods.
1:09:56
And now that I'm deploying the Consul components in the same default namespace. But you could also have them in a separate namespace,
1:10:03
especially if you have multiple applications. That would make sense. Let's check again. So we have these four pods. The first one is server.
1:10:12
Obviously we need the server or the control plane to manage the proxies to inject the proxies and so on.
1:10:20
And the chart name was taken as the prefix as you see here for all those pods.
1:10:25
Then we have the mesh gateway. One instance of it we have the connect
1:10:31
injector that is the one that is responsible for injecting pods. And we have the webhook certification manager.
1:10:39
And as you see all the pods are running successfully. You can also check any other components that were deployed.
1:10:46
So we have this stateful set which is a server itself and those deployments and we have the Consul
1:10:54
services themselves. And one of them is we saw is the Consul UI which is created as a load balancer service type.
1:11:02
And it also gets its own load balancer component on AWS
1:11:08
with its own DNS name. So we can use that to access the Consul UI.
1:11:14
So let's go ahead and do that. And I'm going to make this a little bit broader. And one thing I want to point out here
1:11:21
is that this external service of Consul UI is actually
1:11:26
accessible at the Https port 443. That means we have to access the service using
1:11:34
Http as protocol. Like this. And of course our browser doesn't know the certificate
1:11:42
which is signed by Consul CA so we can say it's all fine,
1:11:47
we allow it. And there you go. This is our Consul UI. And as you see we have only two services displayed here.
1:11:56
So basically Consul now is aware only of two services.
1:12:01
One of them is a mesh gateway which we deployed as part of Consul. And the other one is Consul server itself.
1:12:07
That means another interesting point. The proxies have not been injected yet in any
1:12:13
of the microservices because we need to restart or recreate those services or deployments.
1:12:21
So that's what we're going to do next.
1:12:28
So I'm actually going to delete our microservice deployment completely.
1:12:33
And I'm going to redeploy it with a little bit adjusted configuration. So let's do config dot Yaml.
1:12:41
There you go. And let's see. Looks good. Now, I actually have already prepared a config file
1:12:56
with a couple of changes for Consul deployment specifically.
1:13:01
So I'm going to open this file and let's go through it and understand those changes.
1:13:07
So first of all in order to configure anything in our deployment that is Consul relevant.
1:13:13
So most of the things that are actually relevant for how Consul will treat our deployments,
1:13:19
or whether it will inject proxies or how it will handle the communication between services, etcetera,
1:13:26
we can configure those using the annotations is, you know, annotations are part of metadata of Kubernetes
1:13:33
components like deployments. And these are going to be the annotations on the pod level. So inside the template metadata in the annotations we can add
1:13:42
the Consul annotations basically. So this will communicate our desired configuration of our
1:13:50
microservice sees to Consul, which is a pretty easy way to manage that using
1:13:56
the Kubernetes native way. So the first annotation, which is probably the most used one,
1:14:02
most seen one is connect inject. True. So basically this specific configuration is not relevant
1:14:09
for us because we set the connect inject default to true. Basically,
1:14:16
as I said we can say we don't want auto injection in every part in every namespace.
1:14:22
We want to be able to decide which pods actually get those proxies. And we decide that by adding this annotation
1:14:29
to the pod metadata, right. So every part that we want to have proxy injected,
1:14:36
we can add this annotation and it will take care of it. However, when this is set to true
1:14:41
which is what we configured. And that's what Consul that is deployed in our cluster actually knows, we don't need that.
1:14:49
So I'm just going to comment this out. Let's go to the next microservice.
1:14:56
So we have the same connect inject. We don't need this. And this is another annotation called
1:15:02
Connect Service up streams which is another core annotation which basically defines which services
1:15:10
does this service talk to. And how are those services called. Remember I mentioned that once the proxy is there,
1:15:19
the service inside the pod does not or should not care about where the destination services are located
1:15:26
and what their addresses are. They can just hand over the request with the name of the service,
1:15:32
and then proxy will figure out where that service actually runs in. Kubernetes services are already referenced in this easy way,
1:15:40
using the service name and port instead of static IP addresses. So this is basically not a huge improvement
1:15:47
in this case because Kubernetes already manages that. However, we do need to communicate to Consul which services
1:15:55
this one will be talking to. So that's kind of the metadata definition. And when we have this configured there is one
1:16:02
more change we're going to do here, which is there is an environment variable that points
1:16:08
to the service that recommendations service is talking to.
1:16:13
And in the previous configuration this was actually the Kubernetes service name and the port.
1:16:19
And again going back to my previous explanation, the service does not need to know what the Kubernetes
1:16:27
service name of that microservices that he talks to because it talks to its proxy.
1:16:33
And the proxy will listen to it to this request on localhost because it's within the pod.
1:16:39
So the containers within the pod communicate via localhost and the same port where the upstream
1:16:46
service is configured. So this request will basically go to the proxy instead
1:16:52
of the Kubernetes service. But proxy knows that whatever that request
1:16:58
points to is located here, which is the Kubernetes service name. So as I said,
1:17:05
it's not like a huge game changer here because Kubernetes already manages the service
1:17:11
names pretty well, but that's basically it. So that's the annotation that I have
1:17:17
configured in services. That's the only annotation we use here.
1:17:22
So I'm going to scroll through and comment out all of those connect inject annotations just to demonstrate
1:17:29
that we don't need them. Like this.
1:17:37
So I basically just commented out that annotation, but I'm still going to leave it in the configuration file
1:17:43
for your reference in case you want to use that as well. And then we have two last services that have a bunch
1:17:50
of upstream services they talk to. And it's the same idea. You can just provide a list with service names and ports.
1:17:59
And then all of those will be accessible on localhost on different ports.
1:18:04
So basically the service the checkout service will always be talking to the proxy instead
1:18:10
of talking to all those different services as it was doing before right here.
1:18:15
It will now only talk to the proxy. And then proxy will forward all those requests
1:18:21
to the respective services based on whichever port the proxy receives that request.
1:18:27
And that means obviously those ports need to be different within the localhost and the same for front end.
1:18:35
So front end is the last service which also has a bunch of upstream services exactly
1:18:43
the same concept. Change the localhost here. And there is one more annotation that we are using here for front
1:18:49
end to actually be accessible, which is transparent proxy annotation set to false.
1:18:56
So transparent proxy or transparent proxy true is a feature of Consul that makes it possible
1:19:05
for services to communicate with each other through those proxies, without being aware that those proxies are actually there.
1:19:13
So they are thinking that they're sending the request to the service, and proxies are capturing those requests in the middle,
1:19:20
but services are unaware of that. And with transparent proxy set to false, basically,
1:19:26
we are saying that the service needs to be aware of the proxy, and it has to explicitly send the traffic to the proxy
1:19:34
and route the traffic through it. And that's our slightly modified configuration.
1:19:40
And I'm going to apply. This config Consul file to deploy our
1:19:47
microservices so CTL apply. Config.
1:19:55
Consul and let's see.
1:20:01
And let's give it a couple of seconds for the pods to come up. And. Let's do kubectl get pod.
1:20:10
And there you go.
1:20:17
So let's see what we have here. These are all the pods from the microservices. And you probably notice that for each service or each
1:20:26
pod of the service, we have two out of two containers running inside instead of one.
1:20:32
And that second container is basically the injected proxy. And we can just log one of the service containers to see
1:20:40
what the proxy is doing. So I'm going to do kubectl. Logs and let's just take the edX service.
1:20:47
So I'm going to do this. So basically when you have two containers it takes a default
1:20:53
which is the main container. So this is the microservice itself. However we want to log the proxy container logs.
1:21:00
And this is actually the Consul data plane. So this is the proxy that was injected in the pod.
1:21:07
And we also have an init container. So you need container as you know already
1:21:13
from Kubernetes concepts is basically a container that starts up before the standard
1:21:18
containers actually run. So it's kind of preparing the environment before the rest of the actual containers will run
1:21:26
and init container exits once it's done its job. And then the other containers in the pod will
1:21:32
run and the init container. So this is the Consul process. Basically it prepares the environments for the proxy.
1:21:40
So remember I told you that proxy needs information about what other services are there.
1:21:45
So that if its host service wants to talk to other services, it knows how to reach them.
1:21:51
It also gets the TLS certificate for the secure encrypted communication.
1:21:56
So all of that is actually handled by the init container that injects all this information
1:22:03
into the pod so that the proxy has access to them. So let's actually log the proxy container and what it does.
1:22:11
And we're just going to provide the container name like this. And. There you go. As I mentioned,
1:22:18
Consul's data plane is an envoy container. That's the technology behind it.
1:22:23
So we're seeing the envoy logs and the proxy basically on the startup.
1:22:29
What it's doing is it tries to find the service associated with the pod. So for the edge service,
1:22:35
for example, it will find the associated service and it will register it with Consul so other
1:22:41
proxies can talk to it. Awesome. That means if it doesn't find any related or associated service,
1:22:48
it will actually give you an error that it couldn't find a service associated with that pod. And this now means that all those proxies actually did
1:22:56
the work of registering these microservice pods with Consul.
1:23:02
So this means if we go back to the Consul UI, we're going to see all the services listed here.
1:23:10
Because now Consul knows about them. And for each service it also shows you how
1:23:15
Consul is aware of those services. And in our case they have been registered with proxies.
1:23:21
And we actually have a pod in our cluster that is crashing. So the proxy is up.
1:23:28
However the service itself is not able to start up. That's why we have just one container which is the proxy
1:23:35
up and running. And we see that here as well. Basically it's failing the health check which means
1:23:41
it's not accessible. This means that all the other proxies will actually know
1:23:46
about the issue of the service, without even sending a request to it.
Configure Access Rules
1:23:54
And we can click inside the service. And what this basically displays is not which service
1:24:01
talks to which other service, because payment service is obviously not talking to all of them, but rather which service is allowed to talk
1:24:09
to which service. And right now we have no rules in the cluster that limit any service to talk to any other service.
1:24:17
And that's why everything is allowed. However, we can change that. So for example, if we go back to our configuration.
1:24:24
And I'm going to go to the payment service. You actually see that the payment service is not initiating communication with any
1:24:32
other service. So there is no service that payment service directly talks to. However,
1:24:38
there are services that send the request or initiate request to the payment service, which is the checkout service.
1:24:45
So this is actually the only service actually that talks to the payment service that initiates
1:24:51
the request. That means all of these other connections here that we are allowing are actually not necessary.
1:24:58
So by limiting those connections and basically saying payment service should not talk to anything
1:25:04
other than the checkout service, we are reducing the attack surface in our cluster.
1:25:09
So that means if there was a bug in the payment service, like a huge security vulnerability,
1:25:15
we would actually limit the damage that someone can do by exploiting the vulnerability
1:25:21
in the cluster, because we're limiting what payment service can do within the cluster and who it can
1:25:27
communicate to and talk to. And we're going to use the concept of intentions here. So this is the micro network segmentation
1:25:34
that I already explained, in which Consul basically allows us to define
1:25:40
firewall configurations in a granular way on a service level. And that feature is called Intentions in Consul.
1:25:47
And there is an intention CRD file that you can create as a Kubernetes manifest file, which is pretty simple to configure.
1:25:54
And we're going to create an intention where we're going to say that the checkout service is going to be able to initiate
1:26:04
communication to the payment service, which is what we have right here,
1:26:10
because checkout Service will be talking to the payment service, not vice versa. And that's it.
1:26:17
No other service is allowed to do that. And let's create that. And we can create another intention that says all
1:26:25
the services are denied to talk to the payment service.
1:26:30
So basically by default we disallow any communication and we only allow it for checkout
1:26:36
service as an exception. If I go back you see that this diagram has changed.
1:26:42
And we see checkout service is the only one that can talk to it. And going back,
1:26:47
we can also create another rule where we can say the payment service itself to all other
1:26:53
services is also denied. So let's save this. Go back to topology. And there you go.
1:27:00
And as you see, this is on a specific service level. However, you can do this for your entire microservices application group.
1:27:08
And we even have a warning here that basically tells us to configure that for all the services.
1:27:13
And you can do that here directly as well. But as I said, if you want to automate this, if you want to have that again,
1:27:19
configuration as code, which is the recommended way of working, you would create the Crds for Consul called
1:27:29
service intentions. So we have successfully deployed Consul in the EKS cluster and configured it to inject
1:27:38
proxies into all the microservices, plus the ready service that we're using, which is a third party service obviously.
1:27:44
So it lets us have the proxy application in any service,
1:27:49
whether it's our own third party or whatever, to have that consistency in the communication between
1:27:56
the services which is actually great because we can apply the same kind of rules
1:28:01
on third party applications as we can on our own application, so we can decide which services can talk
1:28:07
to the database using intentions, and we can encrypt the connection with the database the same way as we do
1:28:13
within our own applications. Now, as a next step, we're going to repeat the same exact deployment
Create on connect to 2nd K8s cluster
1:28:21
in another Kubernetes cluster on another cloud platform. So we're going to recreate the same exact
1:28:27
state in another cluster. And then we're going to connect those two to simulate a failover.
1:28:34
When a service here fails that the same service in another cluster on another cloud
1:28:40
platform can take over its job. So we're going to deploy the same application in an Elk cluster.
1:28:49
So I'm going to go ahead and log in into my linode account.
1:28:57
So if you don't have a linode account yet, you can sign up. But also, as I mentioned previously, you can actually create this cluster wherever you want.
1:29:05
The concept will be exactly the same, so it's not anything that is ECS or specific.
1:29:12
This could work with any two Kubernetes clusters. I personally like linode because it makes the cluster
1:29:18
creation super fast and super easy. That's why use it. But you can use whatever you want.
1:29:24
So going to Kubernetes I'm going to create a cluster I'm going to call these Elk Consul. Not very creative.
1:29:32
And I'm going to create these also in the Frankfurt region, but it could be in a different region as well. It really doesn't matter.
1:29:38
Just choose the latest Kubernetes version. I'm going to choose no Aicha for the control plane,
1:29:43
because we just need a demo here. And let's choose the cheaper linode machines
1:29:50
by switching to the shared CPU. And let's take the four gigabyte sized VMs,
1:29:57
and let's choose two nodes. Let's confirm that.
1:30:02
Create a cluster. And this should be up and running pretty fast.
1:30:09
So let's wait for the provisioning of those worker nodes. Our two nodes are running and we can now
1:30:16
download the cube config file to access our cluster. So I'm going to go back to my Visual Studio Code
1:30:24
and open a new terminal. And let's go into the Kubernetes.
1:30:31
Folder again, and we're going to have to export that cube config file to connect to the cluster.
1:30:38
So right here in this execution environment basically we have executed the AWS command to add
1:30:46
the cube config file in a default location where kubectl will look for it. So wherever I execute kubectl now in my local environment
1:30:54
it will connect to the eks cluster because that's set in the dot cube default location.
1:31:01
So basically we're going to configure this specific terminal session or this environment to point
1:31:08
to the cube config file of LCC. And then when we execute kubectl commands here specifically it's going to connect to the LCC.
1:31:15
And that's very easy. We're just going to export an environment variable called cube config.
1:31:21
But again kubectl will pick up on and we're going to set its location to wherever that downloaded.
1:31:30
Alki kube config file is that's what it's called. And there you go.
1:31:36
So now if I do kubectl get node this should point
1:31:41
me to those nodes. Very simple. So basically kubectl will first check is kube config
1:31:49
environment variable set and pointing to a specific kube config file. If it is then that's the cluster it connects to.
1:31:56
If the environment variable is not said, it's just going to look in the default location dot kube and try to find the cube config file there.
1:32:04
And for security reasons we would limit the permissions on this file.
1:32:09
So right now it's readable not only for the owner but also for group and any other user. So I'm going to do change mode.
1:32:20
We can set it to 700. So basically remove any permissions from the file to anyone other than the owner. And that's it. Awesome.
Deploy Consul and Microservices on LKE
1:32:28
So we are connected to the cluster, which means we're going to repeat the same exact steps. Install or deploy the Consul helm chart inside the cluster
1:32:37
and deploy our microservices application with the annotations. Let's do it.
1:32:42
And this is going to be a command here. We're calling this helm installation
1:32:48
of the Consul chart. We're using the same version.
1:32:54
The same values file. And this time we are setting the data center to l k value.
1:33:01
So calling the cluster where Consul will run.
1:33:07
So let's execute this and let's check.
1:33:14
Everything that was created. We have our deployments.
1:33:19
The four pods starting up the same exact thing is in ECS.
1:33:25
What Consul also deploys along which I briefly mentioned are the Crds.
1:33:31
So we can also check those get CRD. And there are a bunch of kids here that are
1:33:40
from the LCC itself, so we can actually filter. And.
1:33:46
Let's find only the things that have Consul in it. So basically you have those service intentions
1:33:53
that I showed you and so on. So it actually creates a bunch of crds in the cluster.
1:33:59
So you can configure Consul and different components of Consul in the Kubernetes native way with manifest files.
1:34:06
And you can find the configuration of all the Crds in their official documentation as well.
1:34:12
So let's give it some time to start up. Let's see if the pods are ready. There you go.
1:34:17
And now we can deploy. The microservices application.
1:34:24
Apply config Consul and enter.
1:34:35
In the same way, we see that two containers are starting up in every part of microservices,
1:34:42
which means the proxy containers were injected in each service. And while this is starting up,
1:34:49
let's actually. Check the services.
1:34:56
Because with the same configuration, we have the Consul UI for this cluster
1:35:01
as well as the front end service for this cluster. And as I told you,
1:35:06
it doesn't really matter which cloud platform you use because the concepts are really similar. So the same way is on AWS.
1:35:14
The load balancer component in Kubernetes actually links
1:35:19
to the cloud native load balancer in linode called node balancer.
1:35:25
So this one right here was created. That's the IP address the external IP address.
1:35:30
And we see that here. This is for the frontend on port 80.
1:35:36
And then we have the Consul UI which is accessible with Https
1:35:42
on this endpoint. This one right here. So exactly same configuration,
1:35:48
which means we can actually access this and see the Consul UI in LKY.
1:35:57
And as you see, that's what we called the data center. That's the name we gave to the cluster environment
1:36:05
when we deployed Consul. So it says okay here and here it says x. So it's going
1:36:11
to make it a little bit easier for us to differentiate when we do stuff to connect those to.
1:36:18
And as you see all the services are listed here. And all those parts
1:36:24
except for the payment service have successfully started. Awesome.
Connect the clusters - Add peer connection
1:36:32
Now we have basically recreated the same exact environment in a different cluster,
1:36:39
on a different cloud platform that can allow us to now have a failover. So if something happens to the cluster,
1:36:45
we can always fall back to the cluster. However, we need to first establish that connection
1:36:52
because obviously now these are two separate clusters. So we need to connect them so that the services
1:36:59
in EKS cluster can communicate with services in cluster.
1:37:04
And for that we are going to create what's called a peer connection. So we're going to make those two clusters peers.
1:37:11
And since both of them have full Consul deployments inside on the Consul level,
1:37:17
we are going to connect them so that services inside those two clusters can communicate with each other.
1:37:22
And it is actually pretty easy to do. Again, there is an option to do this using the CRD components.
1:37:31
for this demonstration we're going to use a more visual and simpler approach of Consul UI to establish
1:37:40
that peer connection. And in the Consul values file, remember we enable the mesh gateways.
1:37:45
These are the components that are actually going to help us connect those two clusters together.
1:37:50
So the mesh gateway in EKS cluster will connect to the mesh gateway in cluster.
1:37:56
So those two are the connection links. And when we have Consul clusters on different
1:38:02
networks like we do here, completely different networks, different cloud platforms, then we're going to need to set the Consul
1:38:09
servers or the control plane, basically to use mesh gateways to request or accept
1:38:16
the peering connection. So on both sides we're going to actually configure Consul
1:38:22
to use the mesh gateway component to send or accept the peering connection from the other cluster.
1:38:29
And we can do that with one of the crds called mesh. So this one here,
1:38:35
and we're going to have to apply that on both Consul deployments. So going back to my code.
1:38:43
I actually have that configuration file already prepared right here. And you see how simple it looks like.
1:38:50
This is the CRD from HashiCorp. By the way, make sure to check the latest version
1:38:56
in the documentation if you are watching this a little bit later. So we're creating the mesh component with a specification
1:39:04
that enables or basically tells Consul to use the mesh gateways for the peering connection.
1:39:10
And we're going to apply this on both clusters which means I'm going to do kubectl apply. Consul.
1:39:21
Mesh gateway right here. And I'm going to switch to and apply it here as well.
1:39:29
There you go. We can also check that the CD was created.
1:39:38
And as you see, we have this mesh component in the cluster, which,
1:39:44
as I said, will allow to route the peering traffic through the mesh gateways.
1:39:50
And now we are actually ready to pair those two clusters. So first going to the ECS Consul deployment.
1:39:59
So that's our main data center. So to say our main cluster. Not technically but just theoretically for us.
1:40:06
And we're going to go to the peers section. And we're going to add a peer connection.
1:40:11
And we can give the peer a name. I'm going to use LCM. That's going to be the peer.
1:40:18
So that's the name that the peer will be represented by. And we're going to click on Generate Token. And this is basically a secure token that will allow the other
1:40:28
peer to connect to this one. So I'm going to copy this and let's close. And as you see this is the peer name.
1:40:35
And it's pending because the appear basically has to make a connection as well using that token.
1:40:41
So we're going to go to the now the peers at Peer Connection. And now instead of generate token we're going
1:40:48
to do establish peering again name of the peer. We're going to call the other peer X and the token
1:40:56
that I just copied at peer. As you see, super simple.
1:41:01
And here we have this status as well as the health check. Is the peer accessible or not?
1:41:08
And if I switch back this one is active as well. Very simple and straightforward as you see.
1:41:14
Now as the next step we're going to add an exported service configuration in the LCK.
1:41:21
So basically we're going to use an example of one specific service.
1:41:27
And we're going to expose that service or export the service from this pier to make it accessible
1:41:34
for the EKS cluster. That means the services here in the cluster will be able
1:41:41
to talk to that exported service. And we're going to use an example of the shipping
1:41:47
service actually, which means we're going to export this shipping service from the cluster to make it accessible from ECS services.
1:41:57
And I also have a configuration for that. Let's go back right here. I have the exported service.
1:42:03
And as you see the configuration is also pretty simple. We have this CD called Exported Services.
1:42:09
This is the name of the service that we are exporting. And this is the name of the peer that is going
1:42:15
to consume the service. Pretty straightforward.
Configure failover to other cluster
1:42:21
So basically just to demonstrate how this is going to work right now, if the shipping service failed,
1:42:28
a specific feature related to that service will not work anymore because the pod
1:42:33
is not available, the service is not available. So let's click in one of the items.
1:42:39
And if I click on Add to Cart, as you see, everything works because shipping service is up and running. Let's go back.
1:42:47
I'm actually going to. Yeah, I'm going to switch back to the EKS cluster and I'm
1:42:54
going to delete deployment. Let me check the name.
1:43:04
Shipping. Service.
1:43:11
There you go. The shipping service pod should be gone and should be
1:43:21
gone from here as well. And now let's actually try to access the same function again. And as you see,
1:43:29
it's not working because the shipping service is not available. You get the error here as well.
1:43:35
So what we're going to do now is that if this happens, like some of the services in this cluster basically
1:43:43
crash and they're not available, we're going to direct or we're going to forward the traffic
1:43:49
to the peer cluster that has the same service. So the shipping service of the cluster will
1:43:56
basically take over instead of that deleted or crashed shipping service that was running here.
1:44:03
So that's what we want to achieve. So I'm going to bring up the shipping service deployment. Again I'm just going to apply. The config again.
1:44:16
Like this. There you go. It works again.
1:44:22
And now let's configure that failover. So in the LCK. So we have this exported service for shipping service.
1:44:29
And we're going to. Apply this.
1:44:38
And if I switch back to my Consul. UI for deployment.
1:44:46
You see that we now have one exported service, which is this shipping service basically.
1:44:51
It also shows the topology of the connections and the same way in each cluster.
1:44:57
It shows that as an imported service from that cluster. So now if we go back to the list of all the services,
1:45:05
so we have all those other services through proxy, and we have this one here that shows
1:45:12
that the service is actually coming from the peer connection. So we have two shipping services available
1:45:19
for this cluster. Now. Now there's one more thing that we need to do from the case
1:45:24
side to create what's called a service resolver. And again service resolver is its own CRD.
1:45:33
And this is the configuration for the service resolver component.
1:45:39
So basically we're configuring the service resolver for the shipping service since we have two shipping services now.
1:45:47
Right here. And we're saying that we're going to use the failover to the peers shipping service service.
1:45:58
So we are going to need to apply the service resolver in the EKS cluster, because we have those two instances of shipping
1:46:05
service in the EKS cluster. And we are defining a service resolver for them,
1:46:11
saying that this should be basically a failover. So switching back to EKS I'm going to apply.
1:46:21
The service resolver. Let's do that. Create it. And now, the moment of truth.
1:46:27
I'm going to delete the shipping service deployment again in the cluster. And that add to cart feature should still be working.
1:46:37
So let's do that again in the EKS cluster. I'm going to.
1:46:43
Delete the deployment shipping service again. Switch back as you see that one is gone.
1:46:51
And now let's actually refresh again just in case.
1:46:56
Going to any product. And if I click on Add to Cart, it should work by failing over to this imported service.
1:47:06
And let's do that. Awesome. As you see, it used the service from a pure cluster as a failover. Awesome.
1:47:15
So that was basically our demo. I hope I was able to give you lots of new insights
1:47:21
and lots of new knowledge about service mesh technology generally, as well as what concepts and small
1:47:27
details are involved in all of this. If you made it till the end of the video,
1:47:32
congratulations on gaining a lot of valuable insights and knowledge in this area.
1:47:38
We put a lot of work and effort in creating this video, so I will absolutely appreciate. If you like this video,
1:47:44
leave a comment with your feedback and even share with your colleagues or anyone who you think will benefit
1:47:50
from learning these concepts. And with that, thank you for watching till the end and see
1:47:56
you in the next video.
