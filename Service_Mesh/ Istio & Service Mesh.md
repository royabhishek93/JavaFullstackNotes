0:00
in this video you will learn about
0:02
service mesh and one of its
0:03
implementations
0:04
which is istio in order to understand
0:07
the concepts
0:08
we will first look at the challenges of
0:10
a microservices application
0:12
and then we will see how different
0:14
features of a service mesh
0:17
solve these challenges we will look at
0:20
how istio implements service mesh
0:22
and learn about istio architecture as
0:25
well as how to configure
0:26
istio for our microservices application
0:29
istio is
0:30
a service mesh so in order to understand
0:33
istio we need to understand what service
0:35
mesh is
0:36
service mesh is a popular solution for
0:38
managing communication between
0:40
individual microservices in a micro
0:43
service application
0:44
so why do we need a dedicated tool for
0:47
microservices communication
0:49
and what are the challenges here
Challenges of a microservice architecture
0:55
now when we move from monolith to
0:57
microservices application
0:59
we introduced a couple of new challenges
1:01
that we didn't have
1:03
with a monolith application and let's
1:05
say we have
1:06
an online shop application which is made
1:08
up of several micro services
1:10
we have the web server that gets the ui
1:12
requests
1:14
payment microservice that handles the
1:15
payment logic
1:17
let's say we have a shopping cart
1:19
product inventory
1:20
and database and probably some more
1:22
services
1:23
and we're deploying our micro service
1:25
application inside a kubernetes cluster
1:29
now what does our micro service
1:30
application setup need
1:32
to run successfully or what are some of
1:34
the required
1:35
configurations for such an application
1:39
first of all each micro service has its
1:41
own business logic right
1:43
payment service handles the payment
1:45
logic web server handles ui requests
1:47
database persist data and so on now
1:50
services need to talk to each other
1:52
when user puts stuff in the shopping
1:54
cart request is received by the web
1:56
server
1:56
which hands it over to the shopping cart
1:58
microservice
2:00
which will talk to the database to
2:01
persist the data so how do services
2:04
know how to talk to each other what is
2:06
the endpoint of each
2:08
service all the service endpoints that
2:10
web server talks to
2:12
must be configured for web server so
2:14
when we add a new micro service
2:16
we need to add the endpoint of that new
2:20
service to all the microservices
2:22
that need to talk to it so we have that
2:24
information as part of the application
2:27
deployment
2:27
code now what about security in our
2:30
microservice application setup
2:32
generally a common environment in many
2:35
projects will look like this
2:37
you have firewall rules set up for your
2:39
kubernetes cluster
2:40
maybe you have a proxy as entry point
2:43
that gets the request first so cluster
2:45
can't be
2:45
accessed directly so you have security
2:48
around the cluster
2:49
however once request gets inside the
2:51
cluster the communication is insecure
2:54
microservices talk to each other over
2:56
http or some other insecure protocol
2:59
also services talk to each other freely
3:02
every service inside the cluster can
3:04
talk to any other service so there are
3:06
no restrictions on that
3:07
so this means that from security
3:10
perspective
3:10
if an attacker gets inside the cluster
3:13
it can do anything because we don't have
3:15
any additional security inside
3:17
and maybe for small applications they
3:19
don't really have any sensitive user
3:21
data
3:21
it may be okay but for more important
3:24
applications like
3:25
online banks or apps with lots of
3:27
personal user data
3:29
a higher level of security is very
3:31
important
3:32
so you want everything to be as secure
3:34
as possible
3:35
so again additional configuration inside
3:38
each application is needed to secure
3:42
communication between
3:43
services within the cluster you also
3:45
need
3:46
retry logic in each microservice to make
3:49
the whole application
3:51
more robust if one microservice is
3:54
unreachable or you lose connection for a
3:56
bit you want to retry the connection
3:58
so developers will add this retry logic
4:01
also to the services what about metrics
4:04
for your services you want to be able to
4:07
monitor how the services are performing
4:09
what http errors are you getting how
4:11
many requests are your microservices
4:13
receiving
4:14
or sending or how long does a request
4:17
take
4:18
to identify the bottlenecks in your
4:20
application
4:21
so development team may add a monitoring
4:24
logic
4:24
for prometheus for example using
4:26
prometheus client library
4:28
and collect tracing data using a tracing
4:32
library like zipkin for example
4:34
so as you see teams of developers of
4:36
each microservice
4:38
need to add all this logic to each
4:41
service
4:41
and maybe configure some additional
4:44
stuff in the cluster to handle
4:46
all these very important challenges in
4:48
the microservices application
4:50
and this means that developers of
4:51
microservices are not working
4:54
on the actual service logic but are busy
4:57
adding network logic for metrics and
5:00
security and communication etc
5:02
for each microservice which also adds
5:05
complexity to the services instead of
5:07
keeping them simple and lightweight
Solution: Service Mesh with Sidecar Pattern
5:13
now wouldn't it make more sense to
5:15
extract all the non-business logic
5:17
out of the microservices and into its
5:20
own
5:20
small sitecar application that handles
5:24
all these logic and acts as a proxy and
5:27
this small application
5:28
is a third party application the cluster
5:30
operators
5:31
can easily configure through a simple
5:33
api without worrying about how the logic
5:36
is implemented and developers can now
5:39
focus on developing the
5:40
actual business logic and note that you
5:43
don't have to add this sidecar
5:45
configuration to your
5:46
micro service deployment yaml file
5:49
because
5:50
service mesh has a control plane that
5:52
will automatically
5:53
inject this proxy in every microservice
5:57
pod
5:58
so now the microservices can talk to
6:00
each other
6:01
through those proxies and the network
6:04
layer
6:05
for service to service communication
6:07
consisting of
6:09
control plane and the proxies is a
6:12
service mesh
Service Mesh Traffic Split feature
6:16
in addition to the above features one of
6:19
the most important features of a service
6:21
mesh
6:22
is traffic split configuration so what
6:25
is a traffic split
6:26
when changes are made to a payment
6:28
microservice for example
6:30
a new version is built tested and
6:33
deployed to a production environment
6:35
right
6:35
now of course you can rely on tests to
6:38
validate
6:38
the new version but what if the new
6:41
version has a bug that you couldn't
6:43
catch with the tests
6:44
happens very often depending on the test
6:46
coverage so in this
6:48
case you don't want to end up with a new
6:50
version of payment service in production
6:52
that doesn't work it may cost your
6:54
company a lot of money
6:55
so you want to send maybe only one
6:58
percent or 10
6:59
traffic to the new version for a period
7:01
of time
7:02
to make sure it really works so with
7:05
service mesh
7:06
you can easily configure a web server
7:09
micro service
7:10
to direct 90 of traffic to the payment
7:14
service
7:14
version 2.0 and 10 of traffic
7:18
to the version 3.0 which is also known
7:22
as
7:22
canary deployment
Istio Architecture
7:27
and as i mentioned at the beginning
7:29
service mesh
7:30
is just a pattern or a paradigm
7:33
and istio is one of its implementations
7:36
and in istio architecture the proxies
7:40
are invoice proxies which is an
7:42
independent open source project
7:44
that istio as well as many other service
7:47
mesh implementations also use
7:49
and the control plane component in istio
7:51
is
7:52
istio d which manages and injects the
7:55
envoy proxies
7:57
in each of the microservice pods
8:00
now note here that in earlier versions
8:03
of
8:03
istio up to version 1.5
8:07
istio control plane was a bundle of
8:09
multiple
8:10
components you had the citadel
8:14
mixer galley and some other components
8:17
so you had multiple pods when you
8:19
deployed istio
8:20
however in version 1.5 all of these
8:24
separate components were combined back
8:26
into
8:27
one single stod component to make it
8:31
easier
8:32
for the operators to configure and
8:35
operate istio so if you have read
8:38
articles or watch videos where all these
8:40
components are explained
8:41
separately note that this is only
8:43
relevant for the earlier versions now
8:45
you only worry about
8:47
one single istio d component
8:50
so istio architecture is comprised of
8:53
the control
8:54
plane which has esteod component and
8:57
control plane manages a data plane
9:00
which is group of all the invoice
How to configure Istio?
9:06
proxies
9:08
so now the question is how do we
9:10
configure all these above features
9:13
for our micro services in istio as i
9:16
mentioned
9:16
you don't have to adjust deployment and
9:19
service dml files for your micro
9:21
services
9:22
so all the configuration for easter
9:24
components will be done in istio itself
9:27
again having a clear separation between
9:29
the application logic
9:31
and configuration and the service mesh
9:33
logic and configuration
9:35
and the great thing is that istio can be
9:37
configured
9:38
with kubernetes yaml files because it
9:40
uses
9:41
crds by extending kubernetes api
9:45
crd is basically a custom resource or
9:48
custom component in kubernetes that can
9:51
be used
9:52
to allow configuring these third-party
9:55
technologies like istio
9:57
prometheus etc using the same kubernetes
10:00
yaml files
10:01
and apply them using cube ctl without
10:05
having to learn a technology specific
10:07
configuration language
10:09
and adjusting that configuration
10:10
directly inside istio for example
10:13
so using a few sdo crds
10:16
we can configure different traffic
10:18
routing rules
10:19
between our microservices like which
10:22
services can talk to each other
10:24
traffic split configuration the retry
10:27
rules
10:28
timeouts and many other network
10:31
configurations
10:32
and there are two main crds for
10:35
configuring
10:36
service to service communication virtual
10:39
service
10:39
which configures how to route the
10:42
traffic to a specific service
10:44
and once that traffic is actually routed
10:46
to that service
10:47
on top of that using destination rule
10:50
component
10:51
we can configure some policies on that
10:54
traffic light what kind of load
10:55
balancing to use
10:56
to talk to the pods behind the
10:58
destination service
11:00
so overall as you see we create
11:03
these crds custom resource definitions
11:06
in kubernetes
11:07
that istiod component which is is the
11:10
control plane
11:11
will read and convert into
11:15
invoice specific configuration and send
11:18
that configuration
11:19
out to all the invoice proxies so we
11:22
don't configure
11:23
proxies we configure control plane and
11:25
control plane itself
11:27
will then push that configuration out to
11:30
all individual
11:31
invoice proxies and the proxies
11:33
themselves
11:34
can now communicate with each other by
11:37
applying this configuration
11:38
that we define without having
11:42
to go back to the easter control plane
11:45
so they can independently talk to each
11:48
other
11:49
because they have all the logic and
11:51
configuration they need
11:52
without talking to the control plane
Istio Features: Service Discovery, Security, Metrics & Tracing
11:58
in addition to configuring the proxies
12:01
stod also has a central registry for all
12:04
the
12:05
microservices so instead of statically
12:08
configuring the endpoints
12:09
for each microservice when a new
12:12
microservice
12:13
gets deployed it will automatically get
12:16
registered
12:16
in the service registry without the need
12:19
of any additional configuration from our
12:21
site because
12:22
istio automatically detects the services
12:24
and endpoints in the cluster
12:26
and using this service registry the
12:29
envoy proxies can now
12:31
query the endpoints to send the traffic
12:33
to the relevant services
12:35
in addition to this dynamic service
12:38
discovery feature
12:40
istiod also acts as a ca as a
12:43
certificate authority
12:44
and generates certificates for all the
12:46
microservices
12:48
in the cluster to allow secured tls
12:50
communication between
12:52
proxies of those microservices and
12:55
finally sdod gets metrics and tracing
12:59
data
13:00
from the invoice proxies that it
13:04
gathers they can be later consumed by
13:07
monitoring server like
13:08
prometheus or tracing servers etc
13:11
to have out-of-the-box metrics and
13:14
tracing
13:15
data for your whole microservice
13:18
application
Istio Gateway
13:22
istio has another component called istio
13:25
ingress gateway
13:26
that basically is an entry point into
13:30
your kubernetes cluster
13:32
you can think of the istio ingress
13:34
gateway as an alternative
13:36
to nginx ingress controller so istio
13:39
gateway
13:40
runs as a pod in your cluster and
13:43
acts as a load balancer by accepting
13:46
incoming traffic in your cluster
13:50
and gateway will then direct traffic to
13:52
one of your microservices inside the
13:55
cluster
13:56
using virtual service component
13:59
and you can configure istio gateway
14:01
using
14:02
a gateway crd
Final Overview: Traffic Flow with Istio
14:08
so now the traffic flow in your
14:10
kubernetes cluster
14:12
with all these istio components will
14:14
look like this
14:16
so user will initiate a request to
14:19
a web server microservice in your
14:22
kubernetes cluster
14:23
the request will first hit the gateway
14:25
because it's that entry point
14:27
of the cluster gateway will then
14:30
evaluate
14:31
the virtual service rules about how to
14:34
route the traffic
14:36
and will send it to web server
14:39
microservice and finally that request
14:42
will reach
14:42
the proxy the invoice proxy inside your
14:45
web server
14:47
micro service the invoice proxy will
14:49
evaluate the request
14:51
and forward it to the actual
14:54
web server container within the same pod
14:58
using localhost now the web server will
15:01
initiate another request to a payment
15:04
microservice for example
15:06
so the request will move from
15:09
web server container to the web server
15:11
proxy
15:12
which will then by applying the virtual
15:14
service rules as well as
15:16
destination rules and maybe some other
15:18
configuration
15:20
will communicate with the proxy
15:23
envoy proxy of payment microservice
15:26
using mutual tls and the same will
15:29
repeat for communication between the
15:32
payment service and
15:33
database and all the way back the
15:36
response will be
15:37
returned to the ui and during this
15:39
overall request flow
15:41
the proxies will gather all the metrics
15:43
and tracing information
15:45
about the requests and send it back to
15:48
the control plane
15:49
so we automatically have monitoring for
15:52
our application
15:54
so that's it for this video subscribe to
15:56
my channel for
15:58
more content like this and if you want
16:00
to see
16:01
behind the scenes content and previews
16:04
follow me on instagram as well
16:05
thank you and see you in the next video
Next:
Istio Setup in Kubernetes | Step by Step Guide to install Istio Service Mesh
