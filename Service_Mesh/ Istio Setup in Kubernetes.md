0:00
in this video we're gonna learn how to
0:02
install
0:03
istio service mesh in a kubernetes
0:05
cluster first we will install
0:07
istio core in the cluster the main istio
0:10
component
0:12
then we will install istio add-ons for
0:14
monitoring and tracing
0:16
after that we will configure our cluster
0:18
so that estio can
0:20
automatically inject invoice proxies in
0:23
our application pods
0:25
and finally we will deploy an example
0:28
demo microservices application in the
0:31
cluster
0:31
so that we can see all the features and
0:34
visualization
0:35
for those microservices in istio and for
0:38
this demonstration we're going to use
0:40
a local minicube cluster so let's jump
0:44
right in now if you want to learn what
0:46
istio is
0:47
and what it's used for you can watch my
0:50
other video about it where i explain
0:52
what service mesh is and what istio is
0:54
and all of its use cases
0:56
and then you can come back and learn the
0:58
setup of istio in your kubernetes
1:00
cluster
Download Istio & configure Istioctl
1:05
so the first thing we need to do is
1:07
create or start our mini cube cluster
1:09
and one note here is that istio will
1:12
actually need some resources
1:14
so the default resources that minicube
1:16
cluster gets created with
1:18
will not be enough so in the minicube
1:20
start command
1:22
we're going to provide options to
1:24
increase the cpu
1:25
and memory resources that our minicube
1:28
cluster gets
1:34
and this resource configuration should
1:37
be
1:37
now enough for our demonstration so make
1:40
sure to set those resources
1:42
high and we're gonna start a mini cube
1:45
cluster
1:46
so now that we have our mini cube
1:47
cluster running with enough resources
1:49
we can actually install issio and the
1:52
first thing to installing istio is to
1:54
download
1:55
istio release package locally on our
1:57
computer
1:58
and on istio's official documentation
2:01
page
2:02
actually you have a guide to
2:05
installing istio and in this guide we
2:07
have link to istio releases
2:10
you can also download the latest istio
2:13
release for your specific
2:15
operating system using this command here
2:17
but we're going to do this
2:19
using this istio release link and here
2:22
you have all the releases we're going to
2:24
install the latest one
2:25
and i'm using mac so that's what i'm
2:28
going to download
2:29
make sure to download the one for your
2:31
operating system
2:33
and as you see this is a tar file so
2:36
basically we just
2:37
unpack it or unturn it and we'll see
2:39
what's inside
2:40
so what i'm going to do is i'm going to
2:42
create
2:43
a folder in my home directory i'm going
2:46
to call it istio
2:48
installation
2:51
and i'm gonna move that downloaded istio
2:55
tar file to that folder
3:00
like this and
3:03
let's go to eastern installation and
3:06
right here is our tar file so that's the
3:09
east
3:09
installation folder and here we have the
3:11
tar file i'm just gonna
3:13
double click and unpack it and
3:16
let's actually see what's inside we have
3:18
the executable
3:20
istio binary folder and some other files
3:24
and what we're going to need from istio
3:26
is actually
3:28
an istio control command line
3:31
which is in this binary folder and we
3:33
want that command line tool
3:35
to be executable and right now if i do
3:38
istio ctl
3:43
and execute you see command not found so
3:46
we need that command
3:48
which is here in the binary folder so in
3:51
order to make that command available
3:52
we're gonna add it to a path right to
3:55
executable path
3:56
and we can do that by adding the path to
3:59
this binary folder
4:01
to our path right basically appending it
4:04
so right now this is how my path looks
4:07
like
4:08
like this and basically here we just
4:11
want to append
4:12
the path to this folder here let's
4:15
actually find out what the path
4:17
is i'm going to go inside that istio
4:20
folder like this and i'm going to print
4:23
out the path
4:25
that's it this whole thing here and now
4:27
we can
4:28
append that to the path variable right
4:31
so we have the original one the path
4:35
and separator and we're just gonna add
4:38
this one here slash bin
4:41
and there you go i'm going to execute it
4:43
and now if i do
4:45
istio ctl and execute
4:48
there you go so we have istio ctl
4:51
available or istio control command line
4:54
interface available here because we set
4:56
the path now
4:58
just note that this only
5:01
sets that path or appends that
5:04
executable
5:04
only in this terminal so if i open a new
5:07
window
5:08
and try to do istio ctl here you see
5:12
command not found so it only works
5:14
wherever you
5:15
execute this export command so let's
5:18
close it
5:19
and there you go we have downloaded
5:21
istio and now we have istio ctl
5:24
available
Install Istio in Minikube cluster
5:28
and now as a next step we're gonna
5:30
install istio
5:32
with this istio ctl command inside
5:36
our mini cube cluster so first of all
5:38
i'm gonna do get namespace
5:40
and let's see that we have just these
5:42
default namespaces
5:44
so no istio namespace here and
5:49
right now also nothing running right so
5:52
we have an empty cluster
5:53
and now let's install istio in our
5:55
cluster
5:56
and we can do that very easily using
5:59
istio
6:00
ctl install command that's it
6:03
i'm going to execute it and i'm going to
6:06
confirm it here
6:07
yes and everything is successfully
6:11
installed
6:12
we have istio core then we have istiod
6:15
which is the main process of istio or
6:18
main component
6:20
and ingress gateway so now if i do cube
6:22
ctl get
6:24
namespace right here you see istio
6:27
system namespace got created and let's
6:30
actually check what's inside there
6:33
let's print out the pots
6:36
and there you go we have an istiod pod
6:39
running here
6:40
as well as istio ingress gateway
6:43
now if you already know the istio
6:46
service mesh
6:47
architecture you know that we have this
6:49
istiod component
6:51
which is a control plane and we have the
6:53
data plane
6:54
which are basically the proxies that are
6:56
injected into
6:57
application pods right so if you have a
7:00
micro service application
7:01
you would have pod for each micro
7:04
service
7:04
and then istio would inject proxy
7:08
and envoy proxy in each of those micro
7:10
service pods
7:12
so that means in order to see istio in
7:15
action and in order to
7:16
see those invoice proxies we need to
7:19
deploy
7:19
an application a micro services
7:22
application
7:22
ideally where the proxies will be
7:25
injected
7:26
so that's going to be our next step
Deploy a Microservices Application
7:32
and as an example microservices i have
7:35
found actually
7:36
one from google cloud platform
7:38
microservices
7:39
demo project and we're going to use this
7:42
one
7:42
to deploy that in the cluster and then
7:45
use istio service mesh
7:47
for this micro services so in this
7:49
release folder here
7:51
you have kubernetes manifests
7:54
and these are basically kubernetes
7:57
configuration files
7:58
for creating deployments and services
8:01
for
8:02
a couple of micro services so you can
8:05
clone this repository
8:07
and we're going to be using this
8:09
specific file
8:10
i have cloned the repo and i have that
8:13
specific file
8:14
now in this istio installation folder
8:17
right here so that i can execute it
8:20
directly from here
8:21
so right now i'm inside istio folder
8:26
and this is my manifests file so
8:29
obviously this is just kubernetes
8:31
manifest files so we can do cubectl
8:33
apply
8:35
minus f and
8:38
start our services and they will all
8:40
start
8:41
in a default namespace
8:44
and you see a bunch of them got created
8:47
we have deployment and service for each
8:49
one of those
8:50
and now if i do cubectl getpod
8:53
again it's in default so directly here
8:56
you see
8:57
a list of them and all of them are
8:59
getting created
9:00
so we're gonna wait for this one to
9:02
initialize
9:03
and start and make this smaller so we
9:05
can see better
9:07
and let's do get pod again
9:10
and there you go all the pods are now
9:12
running
9:13
all the micro services and it took
9:15
actually around eight minutes for all of
9:17
them to
9:18
come up and get in the running status
9:21
so you might have to just wait a little
9:24
bit for that
9:25
and also i guess because we are
9:27
deploying all this in mini cube and
9:29
because of limited resources
9:31
it's also a little bit slower so i
9:33
assume in a bigger cluster
9:34
this should be a little faster when
9:36
you're deploying
9:38
complex microservice applications in
9:40
kubernetes
9:41
managing your application data will be
9:43
challenging however
9:44
caston who is sponsoring this video has
9:47
made data management in kubernetes way
9:49
easier
9:50
using its k10 data management platform
9:54
k10 basically takes off most of the load
9:57
of doing backup and restore in
9:58
kubernetes
9:59
from the cluster administrators it has a
10:02
very simple ui so it's super easy to
10:04
work with
10:05
and intelligent logic which does all the
10:08
heavy lifting for you
10:09
on top of that casting integrates with
10:12
all major cloud platforms
10:14
so you can easily migrate your
10:16
application from one cluster
10:18
to another with all of its data and
10:20
casting does all of that with
10:22
end-to-end security in mind you can
10:24
check them out at casting.io
10:27
now back to our istio setup so now we
10:30
have our istio core
10:32
and we have the microservices running as
10:34
pods
10:35
now note one thing here that each micro
10:38
service
10:39
has one container inside the pod
10:42
right and you remember i said that istio
10:45
should
10:46
actually inject these proxy containers
10:49
in each of those pots
10:50
so why don't we have two containers
10:53
inside each pot
10:54
or basically why don't we have the proxy
10:56
containers inside
10:57
and the reason is because we didn't
10:59
explicitly tell istio
11:01
to inject proxies in the application
11:04
parts
11:05
and it doesn't work by default right it
11:08
doesn't
11:08
inject proxies into every pod that
11:10
starts in the cluster
11:12
we actually have to configure that
11:14
specifically
11:15
and the configuration for that is
11:17
actually very simple
Configure automatic Envoy Proxy Injection
11:21
what we do is basically we label a
11:24
namespace
11:25
with a label called istio injection
11:27
enabled
11:28
now how do we label namespaces first of
11:31
all let's actually
11:32
see the labels that our namespace has
11:37
and we're deploying our applications or
11:39
microservice applications in the default
11:41
namespace
11:42
so that's the namespace we're going to
11:44
be labeling so qctl get namespace
11:46
default and what you can do is show
11:50
labels and this will give you
11:53
a list of labels for a namespace
11:56
and actually you can do this or you can
11:58
add these
11:59
show labels option for any other
12:02
kubernetes component
12:03
like pods and services etc because
12:07
all these components can have labels so
12:10
default namespace has no labels and in
12:13
order to add the label
12:14
again very easy we do cubectl label
12:19
namespace default
12:23
so name of the namespace basically and
12:25
finally we
12:26
define that specific label again it's a
12:29
key value pair
12:30
and the key is istio
12:33
injection and value is
12:36
enabled so this is something that istio
12:39
will understand
12:40
so we have to name this exactly that is
12:44
to injection enabled
12:45
let's execute and now if i do
12:49
get or show labels again for namespace
12:53
right here you see that label got edit
12:55
and you can add as many labels as you
12:57
want
12:57
to any component so now we can actually
13:00
shut down
13:01
all these parts all those micro services
13:04
and then recreate them to see the
13:06
proxies
13:07
being injected so
13:11
we're going to do cube ctl delete
13:17
the manifest let's delete all of them
13:23
if i do cube ctl get pot now i should
13:26
see all of them terminating
13:30
and now all the pods are gone we can now
13:33
just
13:34
reapply this kubernetes manifests file
13:40
like this and note here that i have
13:42
actually not done
13:43
anything to the existing kubernetes
13:46
configuration files right
13:48
all we did is basically just label the
13:50
namespace
13:51
and we're doing exactly what we did
13:53
previously just apply the kubernetes
13:55
manifest file
13:56
without any modification there right and
13:58
that's the great thing about istio that
14:00
you don't have to
14:02
reconfigure your existing configuration
14:05
or the
14:05
existing kubernetes configuration files
14:09
for the proxies to get injected and now
14:12
if i do cube ctl get pod
14:14
instead of one container per pod you see
14:17
two containers
14:18
which are all initializing and this will
14:22
take some time as well
14:23
and there you go all the pots are now
14:25
running and this actually took
14:27
just two minutes to start this time and
14:31
again as you see two containers per pot
14:34
and now i'm actually going to describe
14:36
one of those parts
14:39
let's take the first one and in this
14:42
describe we're going to see
14:44
the containers in that pot
14:47
so if we scroll up
14:51
right here we have init containers
14:54
is still in it and this is istio proxy
14:58
image and then in the container section
15:01
we have
15:02
our microservices application image
15:04
itself
15:05
so basically this part here or the init
15:08
container
15:09
got automatically injected in this part
15:12
by istio because we don't have that
15:15
container
15:16
definition inside this kubernetes
15:18
manifests file
15:22
so if i open this manifest file and
15:24
search for it there is no proxy
15:27
container definition here or init
15:28
container
15:29
so this is done by issue automatically
Install Istio Addons for Monitoring & data visualization
15:37
so now we have the istio component
15:39
running in a cluster
15:40
that automatically injects the invoice
15:43
proxy container
15:44
into every pod that we create in a
15:47
default namespace
15:49
so we have all that configuration
15:51
already set up
15:52
now that's all great but we don't have
15:55
any
15:56
data visualization for what's going on
15:58
in our micro services
16:00
right so theoretically if you know
16:03
istio again i explained that all in
16:05
detail in this what is istio section
16:07
but istio actually collects the metrics
16:10
from all these proxy containers so you
16:13
have all these
16:14
data about how your microservices are
16:17
performing
16:18
what kind of requests they're getting
16:19
metrics data and so on
16:22
but we don't see any of this here right
16:24
and this is where
16:25
istio add-ons come in and in the
16:28
istio official documentation you
16:30
actually see this integrations part
16:33
and these are add-ons or additional
16:36
elements that you can install with eco
16:39
that will give you all this data
16:40
visualization about the metrics
16:43
tracing and basically what your micro
16:45
services are doing and how they are
16:47
performing
16:48
so we're going to install some of those
16:50
add-ons in our cluster now
16:52
and that is also very simple
16:55
so in this e-sto folder here where we
16:58
have this binary for
17:00
istio control or ctl we have
17:03
a folder called samples and inside
17:05
samples
17:07
we have a folder called add-ons
17:10
and these are actually just kubernetes
17:12
configuration files
17:14
for those services right
17:17
so the integrations that are listed here
17:19
for grafana jaeger
17:21
prometheus etc we have
17:24
those files or configuration files for
17:26
those services
17:27
in that istio installation folder and in
17:30
order to install them in a cluster
17:33
we're gonna apply those kubernetes yaml
17:36
files
17:37
using cubectl apply command in a cluster
17:40
very straightforward so again i'm in the
17:44
istio installation folder
17:47
so from here i can do cube ctl apply
17:51
and then in istio 190
17:55
i have samples and add-ons
17:58
and i can apply those files one by one
18:01
or if i want to apply
18:02
all the configuration files in the
18:04
folder i can do it
18:06
like this so execute and
18:09
there you go so you see that a bunch of
18:11
stuff got created we have
18:12
services deployments config maps etc you
18:15
actually don't need to understand all
18:17
those
18:18
components what's important now is if i
18:21
let's actually clean this up
18:25
if i do cube ctl get pod
18:29
from the istio system namespace where we
18:32
had two parts running if you remember
18:35
and now we have grafana jaeger
18:38
kiali and prometheus parts running
18:42
or prometheus is starting up let's do it
18:44
again and there you go
18:46
so now we have those four add-ons
18:50
running as pods in istio system
18:54
and in order to access those parts
18:58
obviously we need services
19:00
so let's check that as well istio
19:03
system and we're going to quickly go
19:06
through each one of those services that
19:08
are deployed as
19:10
istio add-ons in the cluster first we
19:12
have
19:13
graffana and prometheus and
19:16
if you don't know prometheus is used for
19:18
basically monitoring
19:19
anything in your cluster this could be
19:22
the servers
19:23
itself memory cpu usage
19:26
as well as kubernetes components
19:28
themselves like pods and
19:29
services and all this stuff so this is a
19:32
monitoring tool
19:33
and grafana is a data visualization tool
19:37
for metrics data now if you want to know
19:39
more details about prometheus and
19:41
grafana i actually have a separate video
19:43
on that
19:44
as well as how to deploy prometheus
19:47
in your cluster so you can go ahead and
19:50
check that out
19:51
if you want to know more as a next one
19:54
we have
19:54
jaeger collector and tracing this is
19:58
actually
19:58
a service for tracing microservice
20:02
requests
20:03
now if you know how microservices
20:06
application
20:07
works you basically get a request in
20:09
your application
20:10
and then that request goes through
20:12
multiple microservices right
20:14
so the request basically gets forwarded
20:17
multiple
20:18
times and that creates a chain of
20:20
requests
20:21
for one request that a user initiated
20:25
and tracing service basically helps you
20:28
trace that whole chain of requests of
20:30
microservices
20:31
from one microservice to another and
20:34
with jager you can then
20:36
visualize that data right you can see
20:38
those tracing
20:39
data for those requests and you can use
20:42
that to analyze and debug and see where
20:45
the request basically slows down etc so
20:48
that's tracing
20:49
and we also have zipkin here which
20:52
actually is an
20:53
alternative to jager right so in your
20:56
cluster
20:56
when you deploy istio add-ons you should
20:59
have just
20:59
one of those two and the reason why we
21:01
have a zip key in here as well
21:04
is because in this addons folder we have
21:06
grafana jaeger kiali prometheus
21:09
but we also have this extras folder
21:11
which
21:12
contains the zipkin yaml file right so
21:15
that one also got deployed because it's
21:17
also a kubernetes
21:18
configuration file so we have it here as
21:21
well as we have prometheus operator yaml
21:23
file in this extras folder
21:25
which basically is configuration
21:28
to monitor the easter components
21:31
themselves
21:32
with prometheus and for this to work you
21:34
actually have to have prometheus
21:36
operator already installed
21:38
in your cluster which we don't have in
21:41
our cluster
21:42
now again if you want to know the
21:43
difference between prometheus operator
21:45
and this prometheus or what grafana is
21:48
i have own video about that that
21:50
explains all these in detail so you can
21:52
go watch that
21:53
and finally we have a service here
21:56
called kiali which is actually
21:58
my favorite service for working with
22:01
microservices because it has
22:03
an amazing data visualization features
22:06
as well as features to actually
22:09
configure
22:10
your services setup and communication
22:13
so we're going to take a quick look on
22:16
kiali
22:16
and how it looks and basically we have
22:19
all types of visualization
22:21
including the monitoring data in the
22:24
tracing data
22:25
because it's so cool actually we're
22:26
going to take a very quick look at
22:28
kiali specifically in our demo
Kiali - Service Mesh Management for Istio
22:35
in order to access kiali we need access
22:37
to its service so i'm gonna do
22:39
cube ctl port forward
22:44
and this is a service kiali
22:48
in an istio system namespace
22:53
and as a final parameter for port
22:56
forward we need
22:57
the port of that service so this will
23:01
configure port forwarding for this
23:03
internal service which we can't access
23:05
from outside
23:06
so i will be able to access it locally
23:09
localhost on this port
23:10
so let's execute and
23:14
that's the address and let's
23:18
open it here
23:22
and there you go this is actually kiali
23:25
dashboard or view and we have default
23:28
namespace and istio system namespace
23:31
and we have 12 applications running in a
23:34
default namespace and these are actually
23:36
our microservice applications and if i
23:38
click inside here
23:40
i switch to applications and i see
23:43
basically some data about the
23:44
applications but the coolest
23:46
feature or part is the graph here
23:49
if i load this graph
23:53
so actually make the graph bigger and
23:56
right here you see
23:58
the network of our microservices
24:02
visualized in this form
24:05
and kali overview and how it works could
24:07
actually be its own video but
24:09
just to give you a very quick idea you
24:11
see that
24:12
just by looking at this graph even if
24:14
you have no idea about
24:16
how those micro services are implemented
24:19
you actually
24:20
see how they communicate with each other
24:22
which microservice talks to which one
24:25
and so on and
24:29
in the service graph basically you see
24:31
these are kubernetes
24:33
services basically that are
24:36
interconnected so you see frontend talks
24:39
to the recommendation service which
24:40
talks to product
24:41
catalog service etc and then per
24:45
application as i mentioned you have
24:49
metrics and traces and everything
24:52
also in one place in kiali so you have
24:55
the traffic
24:56
inbound metrics traces etc
25:00
again there there is much more to kiyali
25:02
which could be
25:03
its own video but you can definitely
25:05
just play around with it and
25:07
check out some features but there's just
25:10
one final thing that i want to
25:13
mention about istio configuration
25:16
and how all of this actually works
"app" Labels in Pods for Istio
25:22
i mentioned that for istio configuration
25:25
you actually don't need to adjust
25:27
anything in your kubernetes
25:28
configuration files
25:30
but there's actually one thing that you
25:32
need to do or you need to have
25:34
in your manifest files for your
25:36
deployments and services
25:39
for this graph here
25:42
to work or this display here to work and
25:45
that is
25:46
a label called app right right here you
25:49
see
25:50
label f and name of the microservice
25:55
and if i search for it you see all the
25:58
occurrences we have them
25:59
in services and
26:02
deployments and app label
26:06
actually has a special meaning in istio
26:09
so whenever you're deploying your
26:12
microservices
26:13
in istio enabled cluster you actually
26:15
have to have this
26:16
app label on your deployments and
26:18
services
26:20
for the data visualization to work i
26:22
mean the pods will still deploy you will
26:24
not have any errors
26:26
but the visualization will not work like
26:29
this right
26:30
and as you see here the names at service
26:33
front end
26:33
these actually are the values of app
26:37
label here and in the applications tab
26:42
also as you see we have
26:45
for each application these are the
26:49
deployments basically
26:50
you have these app label so that's how
26:54
istio basically knows how to visualize
26:56
your application graph
26:58
and the communication like this
27:01
so that's the one thing you would
27:03
probably need to adjust in your
27:04
kubernetes configuration files so that's
27:07
how you install
27:08
istio in your cluster how you deploy
27:10
additional
27:11
add-ons in order to visualize metrics
27:14
data
27:15
and communication data between your
27:17
microservices
27:18
and how to configure your cluster for
27:20
istio proxy injection
27:23
thank you for watching and see you in
27:25
the next video
