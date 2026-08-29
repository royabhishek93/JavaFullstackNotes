0:00
hey everyone welcome back to the channel so in this particular video we are going to discuss 100 react interview questions
0:06
and answers with code example for beginners now this video is only for those who already have idea on react and
0:13
Redux and you can basically use this video for your revision purposes now
0:18
before starting the questions I want to talk about one of my friend's YouTube channel so he uh recently started his
0:25
YouTube channel in his channel he basically said a lot of things so I'll quickly uh play a video and in that
0:31
particular video we will basically tell you uh the channel introduction and what are the things that you can basically
0:38
gain Advantage from his channel so I will highly suggest all of you please subscribe to his channel I will leave
0:44
the link in the description below he's currently at almost 800 uh subscribers so plan is to complete 1,000 subscribers
0:51
as quickly as possible so uh I will highly suggest all of you that please subscribe and give him some support so
0:57
let's see that video and after that we will be starting uh all the questions one by one let's get started and good
1:03
luck hello everyone my name is Kapil Kumar aanii I'm working as a senior soft engineer for Walmart India recently I've
1:10
started creating Tech content through my YouTube channel which says Tech M couple
1:15
and my channel is dedicated to uh programming Tech tutorials uh Tech interview preparation and soon I'm going
1:22
to build a dedicated playlist uh with core JavaScript Concepts in Hindi also
1:28
I'm going to create a blind lead code 75 programs another playlist in Hindi so
1:33
please like share and comment on my videos okay so we'll start with the first one definitely what is react J now
What is React JS
1:40
here you first need to give the theory because once you'll give the answer of this particular question definitely will
1:46
get some counter ex uh counter questions after this so react is basically open
1:51
source JavaScript library which is developed for building user interfaces particularly single page application
1:57
right so this will be the basic definition of what is react jsis so react the whole concept of react is
2:04
based on creating reusable component UI which is basically to create single page
2:10
application sought for spa so this will be the main definition of reactjs now let's move on to the next one all right
Major Features of React
2:18
so question number two what are the major features of react now here you can basically mention the following points
2:24
now try to keep each and every Point simple and concise the reason is because from each each and every point of these
2:31
you can get some counter questions all right so the first one is virtual Dom so
2:36
react basically uses a virtual Dom right so we have a original Dom and then we have a virtual Dom so what basically
2:42
does re react basically uses some kind of diffing algorithm to see the differences between the original Dom and
2:49
the virtual Dom so here you can see that so we are having react uses virtual Dom which basically nothing was improve
2:55
performance by minimizing direct Dom manipulation so only whatever things
3:00
that needs to be updated in our original Dom so react will only uh basically
3:05
update those things next react uses jsx which is nothing but JavaScript XML
3:11
which allows writing HTML in our react components third Point components so
3:17
react is basically a component based library right so we have different different components which basically
3:24
makes react more reusable all right so that means the UI is basically built using usable components then we are
3:31
having one way data binding very very important so in react data Flows In One Direction right now what are the
3:38
advantages of this so it basically makes the application easier to understand and
3:43
Dew work now if you know some idea about the angular angular basically uses two-way data mining after this we have
3:51
high performance obviously because because of this concept of virtual Dom in react application you have the
3:58
performance will be high all right because it basically does some effective rendering of the components and last
4:04
again un directional data flow right data flows in a single Direction which provides better control over the enter
4:11
applications so these all the points you can mention that uh what are the major features and also you can mention if
4:17
your interviewer ask you this question like what are the main advantages of using react so this for that particular
4:24
questions also you can also mention the following answers this is done now let's move on to the next one now what is
What is Virtual DOM
4:30
virtual D right so you can see that I given for each and every questions I've given the exact uh definition so that
4:36
these kind of definition you can basically explain to your interviewer and after that if your interviewer ask
4:42
you some queries from that you will be basically able to uh explain your interviewer by using some diagrams or
4:49
obviously it's always better to give some example using some uh real life code example so here virtual Dom is
4:56
basically lightweight inmemory representation of the real Dom or the original Dom right what basically react
5:02
does it basically keeps a copy of the actual Dom structure in the memory that calls the virtual D right and again we
5:10
discuss in the previous slide what is the main advantage is that so react don't rerender all the components every
5:17
time it only updates whatever changes is there in your uh virtual Dom so that part will be basically updated in your
5:24
real Dom so these all are the uh steps so first we have the rendering of the components then let's say if there are
5:30
any update occurs by any user click or anything so that will be your updating phase then as I already mentioned that
5:37
react uses the diffing algorithm right so it basically checks what are the difference between the real Dom and the virtual Dom and based on that it
5:43
basically does some batch updates right and then at the end this is called the process of reconcillation so after all
5:49
of this react basically updates whatever things that needs to be update updated in your real Dom so this is the concept
5:57
of virtual Dom and how it works let's move move on to the next one now what are the components in react very very
What are Components
6:03
important question and from this particular question there can be many counter questions that you might get so
6:08
first what you will basically explain that components are the build-in blocks of your react application so whatever
6:14
things that you will be creating the UI that is basically from the concept of components so they're reusable pieces of
6:21
UI that can be nested managed and handed independently and after this you will
6:27
immediately tell your interviewer that we have two types of components in react one is the class based component and one
6:33
is the functional component right now once you'll explain all of these you immediately will get uh some kind of
6:39
counter questions okay now tell me about the class based component and give me a simple example right something like that
6:45
or tell me about the functional component or how you can create a functional component so these two questions that we'll be seeing in the
6:51
next two slide so let's move on to the next one again explain class components
Class Based Components
6:56
with example now from this one we will be learning very very very simple example and what I will suggest all of
7:03
you for each and every question that I mentioned try to do a handson coding so
7:08
from this diagram you can try to implement by your own so first thing what you'll mention that okay first we need to import react and the component
7:15
from react so class based components start with a class keyword very very
7:20
important right then you have the name of the component name of the component always start with caps right this is
7:27
very important which extends the component library from react now here what basically is does we have this
7:34
render method so what this render method does this basically render the jsx that
7:40
needs to be rendered in your browser so this render method basically Returns the jsx and this is nothing but your jsx
7:47
which you will be seeing in your browser right so again I repeat again so you have the class keyword then the name of
7:53
the component which extends the react component from react then we have rendom
7:59
method so this render method will return the jsx that we want to see in our browser and at the end we need to export
8:06
this component so that we will be able to use it in our main app component so this is how you need to create class Bas
8:13
component now let's move on to the next one now very very important explain functional component now most of the
8:19
times I can guarantee in your interview you will get let's say 90% of the questions based on functional component
8:26
because functional components are used nowadays in all the application and it's very very important so in your interview
8:32
will tell that now see normally in interview two two types of things happen right either you have a like uh only
8:39
theoretical interview where interviewer only ask you like tell me in theory and then you have a Hands-On coding
8:44
interview so here in that particular kind of interview uh what your interview
8:50
will tell that okay tell me each and everything and give me proper example okay now this depends from company to
8:56
company right so now here when you explain what is functional components so
9:01
what you need to basically explain that okay functional component we can create two ways either we can create or use
9:06
normal function keyword or we can create using es6 right so if we are using normal function keyword so we need to
9:13
take the function keyword and then the name of the component again now name of the component again start with the Caps
9:20
right and then because it's a function it will simply return the jsx here directly and this is much more simpler
9:26
right functional component will return the jsx direct L we don't have any render method or anything now similarly
9:32
here in if this is Arrow function nothing but it's a simple es6 arrow function and which will nothing but will
9:38
return the GSX that you are returning here and at the end in both the places you need to export this component so
9:44
that you will be able to use it in some other places so this will be a proper example how you can create functional
9:50
component and try to give two example both that we can create using function keyword or we can also use Arrow
9:56
functions right let's move to the next one now what is jsx so jsx stands for JavaScript XML
What is JSX
10:05
right so what basically does so in normal application how it will happen so you write your HTML then you have a CSS
10:12
and then you have a JS file where you'll do all kind of interactivity your HTML only consist of your basic structure CSS
10:18
for styling and then you have a jss right in your jsx what you do you write
10:24
your HTML elements directly inside your JavaScript so in JavaScript and then you
10:29
you place them in the Dom with using methods without using methods like create element so what basically does
10:36
you can see this structure so this react will do internally so this also you need to explain in your interview right that
10:42
how this is basically working so this is not HTML right but still you are able to see the HTML in your browser correct so
10:49
what will tell that GSX will allow us to write HTML element in JavaScript but we
10:55
don't have to use any methods like create element or append child the reason is because react will internally
11:00
do all of these so here let's see this example very carefully so here what you are doing you're simply returning a jsx
11:07
what react will do react will use this create element so it will basically tell that okay I need to create a H1 tag so
11:13
this will be your H1 and this is the content or the children right this can be nested also so this is the nothing
11:20
but your content and null is because you don't have any attributes here so for example let's say you have
11:27
H1 and then you have a some content here right so you have a Content so you have
11:32
a class name here in this part right so if you add those attributes those attributes will come here so the again
11:39
I'll repeat the uh answer here so you might get get these questions very
11:44
frequently because this is very important so jsx stands for JavaScript XML which allows us to re write HTML
11:51
elements in JavaScript and place them into Dom and then react will basically use some create elements some methods
11:57
internally which will convert this GSX into plain JavaScript all right now
12:03
let's move on to the next one all right so next how to export and import components now this is also very very
How to export import components
12:08
important so here also either you can give the example like we can export a particular component using a default
12:15
export or named export right so one thing is very important I want to mention is that that is these all the
12:22
concepts that we are discussing most of them are actually from es6 JavaScript so it's very very important if you're
12:28
giving react interview you should definitely cover all the key concepts of es6 right so here you can see that I
12:34
already have a component that I created so this is a functional component so what we are doing basically we are doing
12:39
a default export so that means what I'm trying to do I'm exporting this component so that I will be able to use
12:46
it where wherever I requireed to use this particular component right so these kind of things you need to explain that
12:52
why export is required or why you need to export a component so here in our app component or our root component or this
12:59
can be any component where you want to use this you need to import this component and then you will be able to
13:05
use it so until unless you'll export this you'll not be able to import it right so that is the reason uh whenever
13:11
you want to reuse a component you need to export that component either you can do export default or you can also do a
13:17
named export let's move on to the next one now very very important how to use
How to use nested components
13:22
nested components now see as I already told you that react is a basically library of concepts of components right
13:28
so whatever things you'll be creating let's you're creating a layout each and every part of this layout will be a
13:34
component right and there can be some component which can be reusable in multiple pages so for example you can
13:41
see that what we are doing first we have nested component like first I have a
13:46
header component so header is a common right for all the pages or all the uh
13:51
layout that you will be creating in your application so here what I'm doing I'm using a component which is a menus
13:57
component right here I'll be rendering the menu so that means this menu is now nested inside this header component so
14:05
what will happen this menu will be now considered as the child of this component so this header is now parent
14:11
for this menus again here what you are doing again we are importing now the header component in our main app
14:17
component right so if you see right this is this component is now sub child of
14:22
this app component so we have app component there we have nested header component then again this header
14:27
component we are n the menus component so this is how you need to do one very
14:32
interesting point I want to mention whenever you will you will tell these things let's say want to use a nested
14:38
component right if the components are in the same file you notice here right we
14:43
are in the same file so in that case you no need to export this component because you'll be able to use it directly so
14:49
this point also you can mention but if any case you want to use this in other place in that case you need to export
14:55
this component so that you'll be able to import it so this is how you can use nested components now let's move on to
15:01
the next one now one of the key interview questions I'm pretty sure if you're
What is state
15:07
giving beginner level of interview less than let's say less than five years also most of the times you will get this
15:12
question and very very important and whenever you'll get what is state in react you need to try to give this uh
15:19
answer with a proper example right so first you need to give the answer so what is a state right so let's say
15:25
you're creating a react application so state is nothing but a option sorry a object that represent the part of the
15:32
app right that can change example we have a button right and then there is a
15:37
counter value every time you click on this button you need to increase the counter value from 1 to two 2 to three
15:43
right so that means there are some kind of things the value is getting changed and this updated value you need to
15:49
render in your browser so that means someplace you need to store this value right so this value you will be storing
15:55
where you'll be storing in a state right and this is your component state so let's see the definition because it's
16:02
very very important to understand the definition also so state is object that represent the parts of the app that can
16:09
change each component can have its own State very very important key Point
16:16
extremely important which can be that means State can be managed within the component so let's say you having a
16:22
component and this component is having a state that means this state you will be able to manage in that component only
16:29
you can't manage that state outside of this component right and when the state changes what will do react will
16:36
rerenders the component to reflect the new state so let's how this works so we see this example let's see you have some
16:42
tree so this is your Dom and this is your real Dom now whenever this is let's
16:48
say your virtual Dom right and this is your real Dom so you have a button whenever you are changing the counter
16:54
let's say this part is changing from one to two so react what it will do react will basically compare these two things
17:01
and it will see that okay there is a change in this particular place so what it will do it will only update this part
17:07
here and what will happen because the state changes so we need to reender the component so that user will be able to
17:13
now see from one to two right so this will be a proper definition of state now let's see with the example now here now
Example
17:21
when you'll give the interview you need to basically mention your or basically ask your interviewer like uh what kind
17:27
of state example that you want do you want me to give class based example or functional example so I will suggest
17:34
that please try to give both like in your class based component what you need to do first we have a counter class this
17:40
is your component again which extend the component library and here inside Constructor you need to initialize the
17:47
state so here you can see that this is the initializing of State because we writing inside Constructor we need to
17:52
take this do state and this is a object so this is your object now to render
17:58
this state what we we have done we have done these. state. count so this is what exactly we have done similar things you
18:04
can achieve let's say you don't want to take Constructor you can directly state in the body of the class and this is
18:10
actually how I like so what you can do remove the Constructor and then you don't need to take the this because now
18:17
this will basically refer to this class State counter do state so now we will be able to again do the same thing so this
18:23
do state do count is nothing but zero right so this is how you need to do it in class based component for functional
18:30
component again these points we are going to discuss in the later questions also but this is just to give example so for functional component you need to use
18:37
U state from react right so what it will do so here you need to take the state
18:43
variable so this is your state variable now if you see these both compare this is your state variable here and this is
18:48
your state variable here this is the method which will update the state and then you have to take the use use State
18:55
and you need to tell react what is your initial value so zero is your initial value and here it is zero which is your
19:01
initial value if you compare both the concept both are same only how you are
19:06
basically writing so here it is much more simpler here it is little you need to not complicated Al but you need to
19:11
write more so that is the reason people are basically using functional component
19:17
nowadays right now whenever you'll give this kind of answer right you will
19:22
immediately get some kind of counter questions also something like okay now tell me how you can update the state
19:27
using this set account so you need to give those example now let's move on to the next
Counter Questions
19:33
one okay so now we already have right I already told you that you can have some immediate counter questions so you in
19:40
the previous slide if you notice right in the previous SL you mention like what is State and in the next okay now your
19:46
interviewer can ask you like okay tell you already mentioned like what is state now tell me how we can update the state
19:53
so that the component will reender and that updated value we will be able to see in our browser so let's see how
19:59
we're going to do that now again you please try to give both right that state
20:04
in react is updated using set State method in class component and using UST
20:09
State hook in functional component right these two things please mention and we are going to see the same example so
20:15
what we have done again we have initialized the state so this is how you can do initialize right we have done
20:21
initialize the state now we are rendering the state here so this will be this do state. count which will be zero
20:29
for the first time now we have a button on click now you might also think what why I'm going little fast because this
20:36
video is only for those who already have IDE on react right and this video is
20:41
nothing but we'll give you the sum up so that let's see you are having upcoming interview so you will be able to finish all the concepts in very little time and
20:48
I'm pretty sure this is going to help you immensely right so that is the reason I'm not going to much details but
20:53
I'll tell you some overview from each and every concept so that from your side now it's your task to complete all of
21:01
this by your end so try to write all of the code and try to basically Implement instead of using image or what I'm
21:08
trying to say if you're watching this video and you seeing this kind of example try to write this in your vs
21:14
code or something the code editor that you are using so again so we having these do do count which is zero now so
21:21
as I already told you that set State method we need to use so use this. set State and you are basically telling that
21:27
which variable I want to update so on click of this button I want to update the counter variable so this is the
21:33
reason we doing these. state. count plus one and here in the on click so this is
21:38
the method so here we are having this do increment so we are basically telling that on click of this button I need to update the state by one this is how you
21:46
can do in class Bas component in functional component again you need to take or initialize the use St so this is
21:52
your state variable this is the method this is your UST State and this is your initial value and here you need no need
21:59
to take any this do count you need to take only count the reason because you are not in the class this is inside
22:04
function so count will r as zero and then in the function we have again handle click which is nothing but
22:10
increasing the count value by one so set count is Count plus one nothing but it will become two one 2 three like that
22:18
right so this will be the example how you can update state in both class and functional components now let's move on
22:24
to the next one all right another uh very uh like I not say very very important but sometime you'll get like
SetState Callback
22:31
what is set State call back so first see the definition so set State call back method is actually set State method will
22:37
accept a call back as a second argument right and which will execute it once the
22:43
state has been updated so for example you have a button here and you're count increasing the count value 0 to 1 2 3 so
22:51
whenever you call the set State method every time the state is getting updated this call in the call back will
22:58
be able to access the updated state so if you noticed here right we have increment method so this. say state
23:04
which is count is this do state. count plus one so that means from zero to it will become one and then if you just log
23:12
so this is a call back so here you have a call back inside this if you just log this right you will be able to access
23:17
this updated value so here if you log State updated will become one again if you click the button it will become one
23:24
to two so here you'll be able to access the two so what is the purpose the new so what you can do right let's say you
23:29
doing some kind of API call or something and then sorry you are doing some uh
23:35
logic here logic building you're doing and whatever value you want to basically getting that value you want to take
23:41
inside your call back and based on that you can do some kind of like API call or something so that is the reason inside
23:47
this call back you will be able to get the updated state so this is what it is mentioned here right now let's move on
23:54
to the next one now this can be very important question now why you should not update
Why not update state directly
24:01
your state directly explain with example right so what will happen if you
24:06
directly update your state or this is called if you muted your state directly
24:12
so it will not trigger a reender of component and I already told you until unless you will reender so react what it
24:19
does it will every time user do a certain acction react will rerender the UI right so that you'll be able to get
24:26
the updated value and it will read to some inconsistencies in the eyi instead
24:31
you should use set state or state hooks right for class base you need to use set State method for uh functional you need
24:38
to use uh uh sorry you need to use the US state hooks so if you see right I
24:43
already mentioned like increment we are having this do state. count directly we are mutating the state if you notice
24:50
directly we doing this do state. count plus one and this is the incorrect way you should not do this this will not
24:55
reender the component what you can do you can use a set State method that we have discussed in the previous video so
25:02
this is also one of the I think I also got this question two three times while giving interview now let's move on to
25:08
the next one now again very very key now this is also another key question that you will
What are props
25:14
get I can guarantee like less than five years of experience you'll get these questions in your interview what are
25:20
props in react or basically properties right so what is props see props are
25:25
basically a way to communicate with components this is a very simple example
25:31
now you can give something like props are basically used to pass data and even
25:36
handlers to the child components first point props Ure a oneway data flow
25:42
remember as I already told you that react is a react basically done does one way data flow until angular it does two
25:48
way so from parent to child now obviously you can also do child to parent that is called State lifting so
25:54
that we are going to see later very very important third Point prop cannot be
26:00
modified by the child components that receive them so Props are read only
26:06
okay so let's see how we are going to do that now for this one we have a parent component which is function app and we
26:13
have another component which is a child component so what we are doing we are importing or using this component here
26:19
you noticed now props is a property whenever you'll pass a property this
26:24
will receive here as a property right and this will be a object props will be object so now because we're passing name
26:31
as a prop so this will be your key prop key and this will be your value of the prop so now here if you render hello
26:39
props do name so what will happen it will render John once and then it will render J one more time because we are
26:47
calling two times so if whatever value you'll be passing you will be able to get that value right so this will be
26:53
your key or basically prop key or this is the prop value all right so this is this will be the very simple definition
27:00
with example water props now let's move on to the next
Difference between props and state
27:05
one again now I think till now we have learned what is State what is props now
27:10
very important what is difference between State and props okay now let's see so first as I already mentioned like
27:16
state is a buil-in object used to store data that may change over life cycle of
27:22
a component and it it is managed within within the component itself right so each and every component can have it can
27:29
have its state on the other side props which is sought for properties are used to pass data from parent to child
27:35
component right so to communicate between two components as I already mentioned that props read only you
27:41
cannot cannot basically modify it state state is mutable right we can basically
27:47
change it using set State method in class components and using UST State hooks in functional component that we
27:52
have discussed in the previous props are immutable right once passed to a child component they cannot be modifi by the
27:58
child so for example there is a one component and in that component you have a state which you're managing and then
28:05
there is another component this state value are passing to this child component right so you are only passing
28:11
the value here which is read only you cannot change the value in in the child component if your state changes in the
28:18
parent component then only the child value will change so that is the reason it is mentioned that props cannot be
28:24
modified by the child component state is local to comp component right cannot be accessed or Modified by child components
28:31
our props are passed from parent to child component and can be accessed by the child so this I I'll say that first
28:38
two points are very very important if you're able to explain these two it is more than enough right so that's all for
28:44
this particular question now let's move on to the next one now as I already told you like react
What is lifting up
28:50
is basically do one way right so you have one component two component three component you will be able to pass data
28:56
from this to this component and again from this to this like that right so then what is lifting up in react and
29:03
this is also very very important so lifting lifting up lifting state of is a pattern basically where state is moved
29:10
to the closest common ancestor or basically the child that needed to share the state right so what basically is
29:17
mean by that for example I'll give you very simple one so you have one component okay now in this component
29:24
this is your parent and you have another component which is your child right this is parent and this is child what you
29:30
need to do right in this child component you have a button okay now what you need
29:36
to do basically instead of so what you are doing instead of managing the state
29:42
in this child component you want to manage the state from parent component but your button is in child component
29:47
right so somehow you need to basically tell that parent component okay whenever I click on this button update the state
29:53
that I'm managing in the parent so in that case what you can do you can do basically you can pass the
29:59
state to the nearest closest common ancestor right so I think this will be
30:06
little tricky sorry let's see with the example so here you can see that we have
30:12
a app component and app component we are using a child component which is a parent and in this child component we
30:19
are passing two prop one is the count value and one that is a method very very important right now you can see these
30:25
two we are receiving as a Prof here and you have button in this component so that means on click you are managing the
30:31
state in this component if you notice see this one you're clicking button in this child component but you're updating
30:37
the state in the parent component right very very important right and now what will happen also you have initialized
30:43
the state in this parent component also but you are rendering the state in you your child component that is fine but
30:49
here if you notice you're clicking button here but you're updating the state in this component so this is what
30:54
exactly you're are doing so this is somehow you're doing like okay from Child component I basically managing my
31:00
user activity but straight I'm managing in my parent component and this is a very good way of basically managing some
31:06
of the state correct now how this is uh helpful again single source of true
31:12
right because if you're managing state in a parent component you ensure the state is consisted across multiple CH
31:18
components for example this handle in increment you have some 10 more components here and for each and every
31:24
component you need to render the same thing now instead of of managing the state in this component each and every
31:30
child component what you are doing you're managing the state in a single parent component and then you're basically lifting that state up to each
31:37
and every child component right also obviously this will simplify the State Management right because the state logic
31:44
is centralized which is making it uh easier to maintain and dewor so this is also a very very uh important question
31:51
now I will say like this will not get in the very beginner level let's say less than two years or less than one years
31:56
but more than two years you can Bic get this kind of question in your interview all right now let's move on to the next
32:02
one now what is children prop in react so children prop is a special property in react that used to pass content that
32:10
is nested inside a component so what exactly is that so you see here we have
32:16
a child component and we have a parent component which is app component and here what we are doing we are importing
32:21
this component and we are passing a children so inside this component you have a children right and here so you
32:28
have a children now what you can do whenever you'll be passing something inside this component or that is nested
32:33
inside a component here you will be able to render this component in your child component using prop. children so
32:40
whenever you do prop. children react will basically check whatever is there inside this or nested inside these two
32:47
container or basically your component so for example for the first one it will render a paragraph for the second one it
32:53
will render a H2 along with a button right let's say for some other you are passing a H1 then you are passing a
33:00
button then you are passing a span then you are passing a p so it will render all four so whatever simple so you will
33:07
tell in uh like it's a children prop is a special property so whenever we'll pass a Content that is nested inside a
33:15
component so this is a component right so that content you will be able to access using props doch property so
33:23
that's all for this one so let's move on to the next one now what are default props in react
What are default props
33:29
so default props is to set the default values for your props so how you can do
33:35
that for example very very simple one so you have a component which is receiving
33:41
props and it is receiving a props do name see this one very carefully so what
33:47
you can do right you can basically specify here uh uh clearly that okay
33:52
greeting which is the name of your component do default props right this will be default props
33:58
name is guest so what will happen for example you have a app component right
34:04
and inside this app component you're calling this greeting
34:09
component but what you're doing normally what you do so what you have learned like if you're passing a prop you need
34:15
to pass this prop okay I'll pass name sorry so normally we'll pass name and
34:21
then we'll pass some value right so we'll pass a name and then there will be a value but in case if you noticed here
34:27
right we are not passing any prop so if you don't pass any prop but in that component you specify the default prop
34:33
so even if we don't pass anything it will render hello guest the reason is because in the default prop the name the
34:39
value of the name is guest if I pass it instead of guest I'll pass suum so it will render here hello suum because even
34:47
if I don't pass any prop from this component it will take the default one right so this is how you can uh specify
34:53
default props now let's move on to the next one
What are fragments in React
34:59
okay what are fragments in react and its advantages now again it's very very
35:04
simple like fragments are basically allowed to group multiple elements and the advantage is that it basically
35:11
doesn't allow to add extra node to the Dom so normally let's say in react we
35:17
can cannot use multiple elements like this we need to wrap all of these elements inside one parent element right
35:24
you can't basically there should be always one par element in jsx so now
35:29
let's say you want to wrap these your elements let's say li1 and li2 inside a
35:35
paragraph or E if you don't do that right or if you do this if you take e
35:40
here so what will happen this is nothing but a HTML element right so this will add extra e
35:47
in your Dom but if you're using fragment fragment basically doesn't add that one
35:53
doesn't add any extra node in your Dom so you can either import it from react using react. fragment or you can also
36:00
use something like this so this is sort syntax okay so this is all about the
36:05
fragment now let's move on to the next one all right so now next how you can do styling in react JS right now to answer
How to do styling in React
36:13
this one now this uh question can be very vast if you're in very beginner level so you can basically mention like
36:19
we can use different kind of styling like let's inline Styles CSS Styles SE
36:25
CSS modules some libraries like materal UI then you have some other Tailwind CSS
36:30
at CN UI so many other things right and then once you'll tell this to
36:35
interviewer then uh see what your interviewer is basically countering right so they can ask you like okay tell
36:42
me something about inline Styles or tell me or write a very simple CSS style seats and use that in a component or
36:49
create a very simple CSS modules something like that don't try to write all of this uh same time because there
36:56
can be lot of counter questions on top of it so if they're uh asking okay tell me how we can do styling then just first
37:03
mention that we can use some different uh techniques like inline style CSS style seat CSS NGS libraries like style
37:09
components material UI Tailwind CSS and design so many other things if they're
37:15
telling okay now tell me what is inline style so you can tell like okay each and every HTML element that we'll be writing
37:21
in that element we can basically specify specific style property which will be nothing but a JavaScript style object
37:28
right and inside this object we can basically use all the CSS properties that we can think of so this is one way
37:36
of writing inline Styles now the reason this is called inline Styles because you writing in line for each and every
37:42
element next how you can write CSS style seats so to create a CSS style seats or
37:48
css modules the uh approach is same there will be slight differences so for example if you're creating normal CSS
37:54
Styles so create a separate file like Style CSS right and then you write all
38:00
of your style in in that file correct so this will be normal how you write your
38:05
CSS code and then once you do that you need to import that file and then you'll be able to use using class name now here
38:12
again one more thing I want to mention when you will they will ask you like how to use styling please mention like in
38:20
react we need to use class name instead of class right this is very very important and this is also another
38:26
interview question like why we need to use class name instead instead of class and the reason is because you remember
38:32
we have a class based component where we have a reserve keyword class right we have class and then the name of the
38:38
component something like that so so that both will not conflict right so they
38:44
have uh you they're basically telling to use class name instead of using a class
38:49
and then once you do class name in that class name you need to mention the class name that you are using in your style
38:55
but how the CSS model will work so the only difference will be the name of the
39:01
file so first you need to basically use here Styles dot module do CSS right so
39:10
this will be do module this will be the extension file extension then you'll write the same style here and to use
39:16
that what you need to do right you need to use import Styles so this will be
39:22
object so style. modules. CSS will give you object of the CSS that you are
39:27
writing right from style. module. CSS and then to use that what you need to do inside in this class name you need to
39:34
take a bracket and then you need to do style dot the name of the class so this will be style do container let's say you
39:41
have another one which will be style do that class name so the only difference will be again I repeat for normal CSS
39:48
you need to use style. CSS import it and then directly use by the class name for module you need to basically use style.
39:55
module as a extension. c CS you need to import as a object so you need to import import styles from style. module. CSS
40:04
and then you need to use it using style do container style do that class name something like that okay so I think if
40:11
you answer all three inline style CSS style seats and CSS modeles I think this
40:16
will be more than enough because in interview they will not go into much like okay now tell me some other things
40:21
like material UI how you can Tailwind use tailwind syst and those things for a basic prospective this is more than fine
40:29
now let's move on to the next one again this is also very very important like how you can conditionally render
How to conditionally render components in React
40:35
components in react and this is also very again this is a S6 concept right so
40:41
if your interviewer will ask you what is conditional statements or how you can
40:46
conditionally render components both are actually same and here I'll give you both the example how you can do that so
40:53
we can use if right so if this do this
40:58
else do that or you can use stary or you can also use the and this all you can
41:03
use correct so let's see so first you can see that I have a component which is a gitting component and here I'm passing
41:09
two prop so one is e logged in and one is e flag so what I'm doing here I can
41:15
see we are using IF right I will tell you all the uses so you're checking if is logged in return this jsx else it
41:24
will go here and then we are doing tary so you're checking if flag is true
41:29
render please sign sign up if flag is false render please sign in right so
41:34
this is what you can do and if you want to use and what you can do you can do like okay
41:41
condition if this is true and end then render this render H1
41:47
right so this is will be and end so for and you don't need to take a colon right
41:52
because there is no else block for this so if this is true render this for turn you need to check if this is to render
41:59
this or else render that and also you can use if but I'll suggest try to use stary more and also if you're doing some
42:05
kind of map and those things you should not use this and operator right try to use stary so if this or else if you no
42:12
need to render anything simply return render null simple as that okay so you if you get these questions in your
42:19
interview please explain that we can use operators like if we can use and we can
42:24
use and also Turner we can use now let's move on to the next one okay now another very very important
How to render list of data in React
42:32
now these questions I'm pretty sure you will get a hands on right handson I'm I
42:37
mean like if they'll ask you tell me how to Rend a list of data and react what they can do right they will give you
42:43
some data 1 2 3 something like that and you need you they will tell you okay now render all of this in your UI this is
42:50
the same thing what I'm trying to say that whatever questions I choose here right from a beginner to intermediate
42:56
point of view these questions can be framed in a different way it's your idea that how
43:02
whether you are able to basically catch it or not for example how to render list of data in react is similar to let's say
43:09
if they give you some data you need to render it both answer will be same I hope you're getting right so what you
43:15
can do right you first you tell that okay we can use a maap function of es6 to iterate over array and render
43:22
each and every item because map will do like that and then you can do a very simp simple example like create a
43:28
component and pass some data as a prop so we are passing 1 2 3 4 5 right as a
43:35
prop and this data we will be receiving as a prop here and then we are simply
43:40
doing map and this number is nothing but each and every individual number and then we are taking a Ai and simply
43:46
rendering a number all the number right if this is object then simply render the object properties so as simple as that
43:53
if they will ask you okay tell me how to render list of data simply tell then we can use map function to iterate over
44:00
that particular array or whatever data you will be providing me and based on that I'll be able to render it all right
44:06
now let's move on to the next one now very very important this also I will Su
What is KeyProp
44:11
this is a important questions okay so you will basically get this like what is a key
44:17
prop so what is a key prop and what is the uses why react use this so key prop
44:23
is a unique identifier okay each element in a list so again I mention right you will get 1 2 three so each and every
44:31
element is a unique element and what react does using this key prop they will keep a track of this each and every
44:38
element so that if there is any changes in the Dom then these all the keys will
44:43
change right so they will be able to track it now what they will do that simply like in the definition also that
44:50
uh sorry which items have changed which items are added or which is removed correct so how you can do again we we
44:57
are using map and then we are simply using a key prop and then we are doing number. two string so each and every
45:03
number we are keeping as a key here you will also get index but I'll give you the next questions also is basically
45:08
related to index so that is the reason I haven't used this although it is absolutely fine to use indexes as keys
45:15
but try to avoid not using indexes try to give some unique identified something like this okay so this is what key prop
45:22
is now let's move on to the next one see very very important why indexes are for
Why indexes are not recommended
45:28
keys are not recommended so why you should not use uh keys index indexes as
45:34
key so the reason is very simple I'll tell you why so first see the definition that use indexes as keys can lead to
45:41
performance improvements and unexpected behavior when list items are recorded or
45:47
removed it should be unique and stable now see the reason okay now see I have
45:52
some elements right I have John my name sorry not my name I have a John and then
45:59
I have a Sam and I have my name here for each and every let's say we using the
46:04
indexes as key so for index start from zero right it will be zero it will be
46:09
one and for this this will be two okay now what will happen let's say you have
46:15
a button okay and every time you click a button you will add a new user so I'll click a button so the requirement is
46:22
that first time when you'll be clicking you need to add at the end second time when you'll click you need to add at the
46:27
first so first time let's I'll click on this button so I'll add one more let's say JJ and this will become three now
46:35
for this part this is fine if you notice the reason is because you're using indexes as keis right so it will be 0 1
46:42
two three and these all three will be untouched so react will not rerender this three list very very important
46:49
right because these are all the keys haven't changed what will happen next time whenever I'll click I need to add
46:55
item here so I'll add uh GG okay something now the trick comes
47:02
so now you added at that first so now this will become zero this will become
47:07
so zero will become one right this Sam will become one to two and suum will
47:13
become 2 to three see what will happen all the keys will change now although you haven't changed anything in this
47:19
three item react needs to re render all the list I hope you're getting right
47:24
because whenever you change add here this Keys is now zero and all the other keys will change so that means react
47:30
will rerender the whole list that is the reason you should not use try to avoid
47:36
using index as as Keys Try to add use some unique properties like ID you can
47:41
use or you can also merge both ID and index con inate right both you can do
47:46
something like that so this is the main idea whenever you have a very large list what will happen you are using indexes
47:53
so every time list will change and react will render right so that's all for this particular one let's move on to the next
How to handle buttons
48:00
one okay how to handle buttons in react by now I think you'll be able to do it
48:05
because we already have seen some example so first thing what you'll do right now to basically tell these kind
48:11
of things in your interview try to give with the example create a very simple one let's say you have a button take on
48:17
click method so you need to spe specify okay I need to take on click method or even Handler in my button so that every
48:24
time I'll click on this button I need to increase the count and then you need to take the uh function and then you'll
48:30
just update the count by one so this is I'm giving this uh this kind of example the reason because in inter will not get
48:35
like okay now convert this one to typescript do this functionality if very
48:41
less time let's say less than 30 minutes for Theory and then other 30 minutes for Hands-On coding then they will not ask
48:48
you to lot of things so they will first check whether you know all of these things or not and to answer those things
48:54
these things are more than enough okay so this is one thing for class Bas component exact same the only difference
49:00
is that you need to take the this keyword the reason is because you're inside a class you need
49:06
to specify like or basically uh tell that okay I'm now checking the instance
49:11
of this method so you need to take that this this do handle increment this do handle increment nothing but counter do
49:17
handle increment because you are inside this class right so this is how you can handle buttons in react now let's move
49:23
on to the next one okay how to handle inputs in react again so there are two
How to handle inputs
49:30
kind of things we can do in react right so we have controls uh components and then we have uncontrolled this also
49:37
you're going to see later part but try to give like with a very simple one like okay you will tell like we can use some
49:43
control components where form data will be handled by component state so what we need to do we need to take a state we
49:49
need to take a input we need to take a form or button something and then we need to store this input value in some
49:55
State and if every time user will type something I need to change the state so this is what exactly we have done so we
50:02
have a function uh component functional component we have a name State set set
50:08
name which will update the state and then we have use stade method and the initial value now inside input we have a
50:15
type we have a value we also can take a name we also can take a placeholder that is fine now very very important you need
50:22
to specify because the question is related to handle inputs so you need to tell like I need to keep a keep a track
50:29
of this name variable every time user will change right so that means we need to take a on change and in the on change
50:35
we'll take the handle change event so what this will do this will give you event property and here you can
50:42
basically store the event. target. value which is nothing but whatever user is typing in your input right so this is
50:50
how you can store it now once you store it now you will be able to manage it let's say you need to pass this in your API those are different things try to
50:57
keep uh your interview questions very concise if they will they will ask you how to handle inputs give them like uh
51:03
tell them like this so in in react uh we have uh we can manage inputs in two ways
51:08
we can we can create controls component which is basically handled by the component state or we can also create
51:15
uncontrolled uh component that we are going to see later to manage using control components we will take a state
51:21
this state will basically nothing but will store the current value that user will be typing then we can take a one
51:27
change method and then we can set the value in that particular uh method okay so that's all for this particular one
51:34
let's move on to the next one now very very very important okay although you
Life cycle methods in React
51:40
are not using any class based component in your project or if you join that company you'll see that we're not using
51:46
any classb component but still it's very very important to learn all the life cycle methods in react right and I
51:53
actually keep this one very simple the reason is there are a lot more but in your react interview you need to
51:58
basically give the most important one right so we we have three things in
52:03
react whenever from start to end component first time getting mounted so
52:09
whatever you are seeing in your browser then component will be getting updated so for example you're clicking a button
52:15
and you are increasing a count value so it it is in updating phase and then you are in the unmounting when the component
52:21
will be basically being removed from the Dom correct so these three will be the things that you need to mention very
52:27
very important try to give like this only mounting when the component is being inserted into the Dom when
52:34
updating means again when the component State or the prop change and unmounting is when the component is being removed
52:40
from the Dom okay now see I'll create a very simple class Bas component and I have all the three so then they will ask
52:48
you okay now tell me what are the methods for each and every state that you mention just now then you'll tell
52:54
okay for mounting we can use component did Mount so if we do something inside this this will only render one time when
53:02
component will Mount okay then we have updating updating means component did update so here what
53:10
you can do you will tell like this on your interval this component dat update will give give us previous sorry we give
53:17
us previous props and previous state and now we can basically check with the previous prop and the current prop
53:23
current prop will be this dot prop similarly we can check previous state
53:28
and this dot state so if previous prop
53:34
and the current prop there is a change in changes means component is updated if there is a change from the previous
53:40
state and the current state that means there is a component uh State changes something like that so this is for
53:45
updating and then simply for mounting we can use unmount not mounting sorry for unmount we can use component will
53:52
unmount where you can do some kind of like side effects not side effect effects like some kind of cleanup uh
53:58
things that you can do inside component will unmount so these three are the very very important then we have some render
54:04
method Constructor but those thing is fine for beginner level these three will be more than enough mounting updating
54:10
and unmounting now let's move on to the next one all right now we are already in the most popular section of our of this
Hooks in React
54:17
video because the reason why I mentioning each and every company that you will be giving interview for they
54:24
use functional component right and for functional components are based on hooks
54:29
so you will get 100% you will get questions from hooks there is no way for
54:35
beginner level you'll get that is the reason first question I given I also got this when I started my react Journey
54:41
that tell me what are the popular hooks that we have in react explain its uses
54:46
I'm I'm telling about my journey means first time when I started that functional components was not there so I
54:52
use classb component and then they introduce the functional components right so to answer this one simple give this
54:59
one very simple that mention all the hooks and then give one liner answer like what each and every hooks does so
55:06
start with very popular U State we tell manages state in functional component as simple as that use effect manages side
55:14
effects in functional component the reason why I'm telling because they ask you what are the popular hooks now they
55:20
you will tell use effect and then you explaining all of this with example then
55:25
your inter might get irritated also so first keep all this one concise and then
55:31
after this definitely you will get counter example you'll tell use effect and then they'll ask okay now give me
55:37
one example on use effect or give me one example on use effect uh sorry use St something like that so use effect
55:43
manages side effect in functional component use context consume context in functional components or basically use
55:50
to manage Global State use reducer same thing manages State function component but it's used
55:58
as a reducer function and it is for more complex State Management then we have us
56:03
ref which access the Dom elements or manipulate Dom elements use callback for
56:08
performance Improvement use case use memo also for performance Improvement use case as simple as that so these all
56:14
are the main popular hooks that we can use right now let's move on to the next one now next couple of will be based on
56:20
these hooks only right okay I think this we have already done multiple times still I'm going to
56:25
again it what is Us St how to manage it or how you can use it or give with one
56:33
example all of this questions you can give something like this what we can do first you need to explain what is a UST
56:39
so you'll tell okay UST is basically used to manage component state in react components okay now tell me one example
56:47
so every time you give counter you can give some different example also that is fine so you'll tell that okay first we
56:52
need to import Us St from react that is the very important so UST state will take initial value so this is your
56:59
initial value right so this will be your initial value this can be anything it
57:04
can be string it can be number it can be Boolean it can be object it can be null it can be array anything then we have a
57:11
variable which is your state variable and you have set State method then they will ask okay now tell me what exactly
57:17
this two so you tell okay variable this is nothing but the state variable that will be displaying in our browser or our
57:23
our user will be able to see that what exactly we are doing uh let's say we doing some activity or something set State method is nothing
57:30
but will update this variable state right and then you can give example I have on click and I have a method here
57:37
this method is nothing but we are calling the set State dispatch method which is updating the state by one so
57:43
every time we'll click on this button this button changes and sorry the count value changes and count value changes
57:48
means the component state is getting uh changed or getting updated this is exactly how you need to explain so first
57:55
give the Theory prospective and then try to write with a very simple example sometimes they will not ask you uh I'll
58:02
tell you one very interesting thing sometime interviewer will not ask you to write example you need to tell them okay
58:07
can I please uh give one example because for me uh it will be very easy to uh
58:13
explain using example because I'm pretty sure you also know that some questions can be very difficult to explain using
58:21
Theory those kind of questions it will be always better to write example instead of of telling a long Theory
58:27
right so keep this one very simple and then try Say by yourself okay now I'll write a very simple example to explain
58:33
the uses of us usate something like that all right so this is all for this one
58:39
please write all of this in your code editor and try to implement by your own
58:44
I'm pretty sure this will give you very very advantage in react interview because you will get this kind of questions already now let's move on to
58:51
the next one now extremely important or very very
What is UST Hook
58:56
very important right what is use effect hook and how to manage side effects so
59:02
first thing again you need to tell that what exactly is that so you'll tell use effect is a hook that manages side
59:07
effects like we can do so many things like data fetching we can basically check our previous state current state
59:14
we can do some kind of subscription or some manual changing in our Dom element those all of these right so how we it
59:21
works so first you need to again tell okay first we need to import you use use effect from react now use effect will
59:29
take a call back function so this is the Callback function and a dependency array right very very important dependency
59:35
array so then you need to explain your interview each and everything that what exactly this dependency array and based
59:41
on this how this use effect will run so first point you will tell okay if there
59:47
is no dependency means empty array this effect will run only once on page load
59:53
so this is similar to component did Mount in class comp components okay if
59:58
there is a dependency I noted here this us effect will run if the dependency
1:00:05
value changes so here if there it's a dependency if this value change this us effect will run last use effect will
1:00:12
also return a callback function which is nothing but a cleanup method right now this is similar to component will
1:00:18
unmount in class component and this dependency is similar to what component did update in class component right
1:00:25
because this is nothing nothing but you'll be able to see here whether the prop or state are getting changed and
1:00:30
based on that this use effect will run right so this is what will be your example what is us use effect to and how
1:00:37
to manage side effect using it now let's move on to the next one all right so now we have another very very important one
1:00:43
so how to implement data fetching in reactjs now obviously this you are mostly going to
1:00:50
get handson interview questions so they will tell you to implement so they can give you a simple API endpoint right and
1:00:56
you need to basically fetch the list of data now both the next two questions will be interconnected so first thing
1:01:03
what you need to tell okay first I will take a data where I'll be keeping my data or state and use state of null or
1:01:10
you can also take this one as a empty array now as you already discussed that we need to take a use effect and we need
1:01:16
to keep as a empty dependency I already written that empty array means this
1:01:21
effect will run only once because we need to do it on page load now again one more thing you need to ask ask your interviewer that how you want this
1:01:27
functionality you want the data fetching on page load or you want it on button click if they want it on button click so
1:01:34
you need to instead of calling in use effect you need to do this on click on button and we need to do the same things
1:01:39
I hope you're getting so here let's say they will tell you okay now do it for page load so you need to take a use
1:01:45
effect and then we need to create a method so this method will be a simple
1:01:50
Asing method where in the response we'll be using our fet API this will be API point that your interviewer will give
1:01:57
you once you'll get the data back you need to render or save the data in your set State method set data right and then
1:02:05
once you'll get the data you can render the data here or else you can render some kind of loading so obviously this
1:02:11
part we are going to discuss but this is how you need to implement data fetching right now what you can do right take a
1:02:17
dummy API endpoint from Google and try to implement the same thing in your vs code and also see how much time you will
1:02:24
you are basically taking to implement this 5 minutes 10 minutes how much and based on that try to improve see this is
1:02:30
how I also tried because I failed so many interviews where after giving multiple interviews Bas specifically
1:02:37
Hands-On interview then only I'll be able to I was able to master all of this okay now let's move on to the next one
1:02:45
as I already mentioned that how to manage loading State this is interconnected to previous one so what
1:02:51
is basically happens whenever you will do some kind of data fetching right so we have some kind of loading state so
1:02:58
that until unless the data is getting faced from a API end point we need to show some kind of loading data or
1:03:04
loading state in our e so that it will be easy for our user to understand that data is getting fced we need to wait for
1:03:11
some time so what you can do simply take a loading State one more
1:03:17
State and keep this one as false true whatever now what we have done simply the previous part we have done this
1:03:23
assing function right before very very important before you are calling the API
1:03:29
just keep this set loading as true this is the first thing and once you'll get the data back from your API make this
1:03:36
one as false again so this is what exactly you need to do that means the data is getting fced so loading will be
1:03:43
true and if the loading is true you are showing that please wait loading data please wait you are returning here right
1:03:50
and then once you'll get the data you're making this on false so that time this part will be getting rendered
1:03:56
so this is how you can Implement loading set in your uh API call now let's move
1:04:02
on to the next one okay extremely important this is
1:04:07
also I I'm saying important in everyone because this is how I actually choose all of these question because these kind
1:04:12
of things you will get in your interview what is prop drilling or how to avoid it
1:04:18
now please not it down you will not get the exact question in your interview also this question can be framed in many
1:04:25
different ways but whatever things they will ask you need the answer will be almost same first the definition prop drilling
1:04:32
occurs when you pass data through many layers of components and it can be avoided using context API or State
1:04:40
Management libr likea now the question can be something like this what is context API and why we actually need
1:04:47
context API in that case you need to tell okay contest API is basically used to avoid the concept of prop drilling so
1:04:55
what exactly proping is so you have a component right a component component a
1:05:00
then you have another component B component component B you have another component C component and another
1:05:06
component D component in this D component you need to render something so render title but this title you need
1:05:13
to get it from a component right so what you need to do and the path is a
1:05:19
component in the B component is nested in a c component is nested in B and D
1:05:25
component is nested in D so there is no direct connection between a and d right so how you're going to pass it so this
1:05:32
is called the concept of probing so first you need to pass this title from A to B see here I passed a to B then from
1:05:39
B to C same title I'm passing then I'm passing from C to D again as a prop and
1:05:46
then in the D I'm rendering this so This is called the concept of proping so you're passing like this from one
1:05:52
component to another component for now for God's sake this is is only four what will happen you have 40 components you
1:05:58
will do the same thing 40 times right it is irritating you can't do there is no other way so that is the reason we have
1:06:05
something like context but this is the reason why we need all of this so when you are passing your data in many layers
1:06:12
of component so in that case you can basically use or avoid prop dealing using context AP or some libraries like
1:06:18
Redux now let's move on to the next one now next one is what is context API in
1:06:25
react and why is it used again context API is way to share values data or
1:06:31
function between components without having to pass prop in every level just like we have done in the previous one
1:06:37
right so it is used to avoid prop drilling so how this works don't see this one I'll tell you one very simple
1:06:42
example let's say you are having some component a component B component C
1:06:48
component and D component so what we do right context will keep your All State
1:06:53
in one place so this is your context what you can do whenever it is record so
1:06:59
both the components bles are not connected with each other so now in that
1:07:04
case there is no like disadvantages or no problem right what you can do you can simply get your state from this context
1:07:12
instead of passing it in every level right so this is what is so you have a global State managing in one place and
1:07:18
then you are basically using this in all the components wherever it is required
1:07:23
now the thing is there are some process that you need to basically uh follow to
1:07:29
create or manage a context first thing create a context so you need to mention
1:07:34
all of this in your interview that to create a context we need to use create context okay so create context will take
1:07:42
initial value that also you can pass once you'll create a context you need to provide this context so you need to
1:07:48
create a provider what this provider does right this provider is basically give a value property which will be your
1:07:55
state so State Property so how you can do so this provider will take a children
1:08:00
now what this children is again this children is nothing but all of these components child components right this
1:08:06
children is that so what you're doing you're providing this value or the state in all the children so that is the
1:08:12
reason you'll be able to get it and then at the end in your root component not in
1:08:17
app or basically in your root uh component in your application you need to wrap this my provider or basically
1:08:24
this provider so that this context is now accessible in your application if
1:08:29
you don't do that there is no direct connection between your context and the components right so that is the reason
1:08:34
you need to wrap it so we have three step we need to create the context we need to provide the context and then we
1:08:39
need to wrap this context in our root component now let's move on to the next
1:08:45
all right so now next one how do you consume context using use context hook
1:08:51
right so whenever you will be creating the context so context will basically provide the state and from the
1:08:57
components you need to somehow consume that state so the answer will be that we basically consume the context in
1:09:04
functional component using use context hook right so this allows to access the context values directly and it uh very
1:09:12
simple so what we need to do right in the previous example we learned that we need to basically provide your context
1:09:17
right you need to provide the context so once we provide the context you need to First import use context from react
1:09:24
right and then you need to basically import the context that you have created so if I go to the previous slide right
1:09:31
you can see here we have a my context that we have created so here you need to basically first export this so once
1:09:37
we'll export this my context this context will consume all the state variables that you already
1:09:43
created and then first we'll import this my context and in this use context will'll basically receive a context
1:09:51
object and here you need to pass this my context that you have created and this will give you the value so inside this
1:09:56
value you will be able to access all the state that you are having right and whatever value you want to render you
1:10:02
will be able to do that so this is how you need to basically consume uh context using use context hook now let's move on
1:10:09
to the next one all right how can you update context values now this is also
1:10:16
almost similar process the only steps will be first you need to explain like this like uh okay first I'll create the
1:10:23
context so this is my context using Create context then I created my provider so my provider will receive the
1:10:30
children properties and I used my provider uh my context. provider and
1:10:35
here we are passing all the values and this we've already discussed in the previous two slide now once you'll pass all of these value now let's say in this
1:10:42
component you need to consume this state right so in the previous slide we understood that okay now use context
1:10:48
need need to use and then my context the context name we need to pass here now what this will give if you noticed here
1:10:55
in this value property we are passing this value and the said value now said value is a method and value is a
1:11:02
property let's say now these two you will be able to destructure from my context right because this will be
1:11:07
object and now let's say in this component you are having a button which is like some update property or let's
1:11:13
say some click property what you need to do right so you need to update this
1:11:19
value state that you are having inside your context from this component so what we have done we provide the context
1:11:26
first we pass the values here and in the component first we consume the context and then in this button click very very
1:11:32
important you can see that we are basically passing the set Value method here in this button component so that
1:11:38
now if I click on this button this will update uh the state variable in your context so there is no direct connection
1:11:45
but you can see that from your component you will be able to update the state here right so this will be how you can
1:11:50
update context values now let's move on to the next one how do you use multiple
1:11:56
context in a single component now this is very very simple as the name suggest so whatever context you want to use you
1:12:02
need to create all the context let's say you have a first context using Create context second context using Create
1:12:09
context Second Step again you need to provide now again when you have multiple context you need to basically
1:12:16
wrap all of these so first I WRA this mic uh first context. provider I I pass the first value then I pass the second
1:12:23
context provider I pass the second value if you have more you will be able to Nest it and inside that only you'll be
1:12:28
passing basically the children now children is nothing but all your components so now let's say from first
1:12:34
context you need to get the first value from the second context you need to get the second value so what you will do again you need to use the use context so
1:12:41
first use context and then you pass the first context that you have created sorry this context here first context
1:12:47
and for the second one you pass the second context that you have created and then you'll be able to access both first
1:12:53
and second if you have more let's say third context so you will pass again the third context here then you'll be
1:12:59
getting the value here and then you'll be able to access that all right so how many context context you need to create
1:13:04
you can create it the only thing is that you need to provide all of this context here and then you'll be able to use it
1:13:10
in your component all right now let's move on to the next one now again uh this is almost
1:13:17
like the similar kind of things in the prop drilling part also we discussed that what are the advantages of using
1:13:23
context API over prop drilling the the question can be something like this also like how you can avoid prop dring right
1:13:29
so that also have discussed so see here what context API does it basically reduce the need of prop drilling right
1:13:35
so you have multiple component instead of passing the data in each and every level what we can do will keep the all
1:13:42
all all the state in one place and then whenever it is required we will be basically able to get the state from
1:13:48
Context so this is what basically it is doing and also it is making the code more readable and maintainable obviously
1:13:54
right it it allows for easy setting of state and function across the components
1:13:59
without passing the props through every level this is very important so this part you can basically mention that
1:14:05
without passing props through every level what you can do right you can basically create a context which will
1:14:10
nothing but will basically avoid the prob drilling concept so here you can see that without context what you are
1:14:17
doing you are creating having a parent then again child then again grandchild and then you are passing the value
1:14:23
something like this without context St a just create the provider and directly you'll be able to pass it in the
1:14:29
grandchild you no need to Nest it every time so this will be the main advantage of using context API over prop drilling
1:14:36
now let's move on to the next one all right now another very very important hook and uh you might guess
1:14:44
this question also like tell me what exactly use reducer Hook is and when you should use it now see use reducer is
1:14:52
basically a alternative of use St all right so we have used State hook right usate basically used for State
1:14:59
Management so here used reducer Hook is basically used for State Management only it is suitable for handling more complex
1:15:06
State logic so whenever you have multiple things that you need to manage multiple State and everything it's
1:15:11
better to use use reducer instead of use State the reason is because this is
1:15:17
nothing but manages the state using a reducer concept so all of these will be in one place and it is much more
1:15:22
maintainable and also readability will be more so here you can see that how we are going to do the that so first we
1:15:28
need to import use reducer from react and then we need to take a state variable right then there will be
1:15:35
dispatch method we are going to discuss what exactly this dispatch method does
1:15:40
but first we have a state we have dispatch we need to take the use reducer that we have imported from react then we
1:15:46
need to pass the main reducer function which consist all of this logic and then
1:15:51
we need to pass the initial State okay now let's understand with this right even if the even if your interviewer
1:15:58
tell you okay tell me with a simple example give this kind of example only instead of count you can also give like
1:16:03
flag Also let's you keep a flag as false and then create a button and then on click of this button make this flag as
1:16:10
true then create another button and make this one as false something like that so what it is doing this state will
1:16:16
basically give you the updated State dispatch will dispatch a method so
1:16:21
here we have a two button right and we we have a plus button and we have a minus button on click of this I want to
1:16:28
increase the count so you'll tell that okay whenever I'll click on this plus button I will dispatch accent and now
1:16:34
what accent basically does this will have a mandatory type property so this is mandatory right type is basically
1:16:41
will uh tell that okay for this particular dispatch acction what exactly I need to do in my reducer for this one
1:16:48
I need to do type of increment for this button I need to do type of decrement let's say you have another button there
1:16:54
you need to do type of reset when you pass this one in your reducer reducer will consist of the state which return
1:17:01
the updated State and also the acction this accent is basically have a type now
1:17:06
this type is nothing but this type that you are passing here so what basically it will do based on different different
1:17:12
cases so you took a switch statement now you have a case of increment so okay so whenever you'll click on this plus
1:17:18
button it will check that okay now type is increment that means this case I need to consider or I need to execute
1:17:24
whenever I do type of decrement the reducer will understand okay now we have a case of decrement so I need to
1:17:31
decrease the count by one when I have a increment I need to increase the count by one and once this is done it will
1:17:37
give you the updated state right and this updated state from where you will be able to access from this state so
1:17:43
this is your state right so this state will have your count property so you have this count right if I do state do
1:17:51
count see similarly what we have done so you'll be able to see the account value in your browser right so in sum up what
1:17:58
we we have done so we have imported use reducer from react which will take a state and a dispatch method dispatch
1:18:04
will dispatch the accent with a type property and this type property is basically used to identify different
1:18:10
different cases and whenever there is a case which will satisfy it will return
1:18:15
the updated state if nothing then it you can return error or you can basically simply return the state here so this is
1:18:22
all about the use reducer hook now I highly suggest please practice this one by your own right create a simple
1:18:29
example and try to do it now let's move on to the next one now here uh this is a
1:18:34
very simple one like you might get ask okay uh give me some example with complex State object with use reducer
1:18:41
you no need to do anything what you can do right simply let's say take anyal State instead of passing only count pass
1:18:48
another text property or let's say a flag property right and whenever you are doing increment that time let's say you
1:18:56
will increase the count by one and whenever there is another case right let's say there is another button which
1:19:02
will update the text and in that case what you can do right you can basically pass some text property and then you can
1:19:07
update the state so this is just to give you example that in this initial State you can have multiple nested object and
1:19:13
those you'll be able to easily manage using used reducer so if your interviewer is asking you okay can we
1:19:19
basically use used reducer for complex State objects the answer will be definitely yes because this is why why
1:19:25
use reducer is alternative of use State because this basically used to manage uh complex State Management Logics all
1:19:32
right so now let's move on to the next one how do you pass additional arguments to a reducer function right now this is
1:19:39
also very very simple what we need to do right you remember in the previous one right here we are passing dispatch and
1:19:45
there we are passing a type of increment in this dispatch object type is always mandatory I already told you right you
1:19:51
can also pass some other properties also that that you will be able to access in your reducer for example let's say you
1:19:58
have dispatch method and here you have a type of update so type of update means this case will be updated uh this case
1:20:05
will be uh executed and here in this uh object you are passing additional uh
1:20:12
property additional argument and that is the question and here you're passing a payload and inside this payload you're
1:20:17
having a value so how you will be able to access it so you can see that we are having access. type similarly you'll be able to uh use it using access pad. Val
1:20:26
access. pad. Val and this what we are doing so we doing access. payload Dov
1:20:31
and this is not about only returning but what you can do using this value you can do certain things right in this case
1:20:37
let's say you need to do API call not API call but some manipulation data manipulation you need to do and based on
1:20:43
that you need to return so if your interviewer is asking you how you can pass additional arguments to reducer
1:20:49
function the answer will be that whenever we dispatch action it will have a type right and in this object we can
1:20:56
basically pass additional properties like payload or whatever and that we'll be able to access inside our reducer all
1:21:03
right so that's all for this particular one now let's move on to the next one all right another one now this you can
1:21:10
get little intermediate level of interviews not for beginners like how do you handle side effects using use
1:21:16
reducer now this is actually possible now let's see with the example right so first we have a initial State and there
1:21:23
I have a data null and loading is true right so this data I need to get it from a API input first I took a state I have
1:21:32
dispatch I have used reducer and then my reducer function is this and initial state is my data null and loading true
1:21:40
now what we are doing let's see because we need to fetch the data on page load so what we need to take we need to take
1:21:46
use effect right and empty dependency means this will run only once and here you do the API call so you
1:21:53
do the API call so you have AP Endo we are getting the data once you'll get the data very very important that time you
1:22:00
are dispatching a type that okay my data is now fetch success and then my payload
1:22:05
is the data so this is the additional argument that we have just discussed right so here now this payload data
1:22:12
where you'll be able to access accent. payload right if I do accent. payload what it will give you it will give you
1:22:18
the data that you're getting from your API response correct so that means you can tell your interviewer that we can
1:22:24
Implement a use effect inside this use effect I'll do the API call and then once I'll get the data back that time
1:22:30
I'll do a dispatch and in that one I'll pass a type so it will come here and then I'll pass the data so data will be
1:22:37
your accent. payload so this accent. payload and loading you can make this one as false right so the answer is like
1:22:44
if they ask you that can you handle side effects using used reducer and then store the value instead the answer will
1:22:50
be yes and this is how you can do it all right so now let's move on to the next
1:22:55
one now next one is also another very important interview question that what is usuk right so the answer will be us
1:23:03
rep Hook is used to access and interact with dom elements right also you it can
1:23:10
also use for uncontrol form elements and those things and what basically the advantage is that this is basically
1:23:16
takes a mutable object right which will persist the values without causing
1:23:22
rerenders every time so what you let's say you're doing some Dom manipulation and you are storing some value inside a
1:23:28
ref what it does it will not rerender every time right so that is the reason
1:23:34
you can use use rep in those use cases for example let's say you have a requirement if they ask you okay now I
1:23:39
got your answer now tell me with a simple example so what you can do right okay so you can do that uh let's say I
1:23:46
have a input and I have a button click what I need to do right on click of this button
1:23:52
I need to focus on this input so Focus means it will be like focused outside border something so here you can tell
1:23:59
you interview that okay I can use here some R property so first how you can do
1:24:05
again first you need to import use ref from react and then you need to create your input ref right you need to create the
1:24:12
ref element so use ref will take again the initial value so in this case this is null and then you need to basically
1:24:20
pass this input ref to the Dom element that you want to use for example for this input I want to use this input
1:24:26
ra so to pass a ra what you need to do you need to use this ra property and this has to be ra only so in this ref I
1:24:33
pass my input ref right and then on click of this what I'm doing this input
1:24:38
ref will give you a current property very very important this ra will give you the current property and inside this
1:24:44
current property you'll get lot of things like all the things that you need so from here you need to get the focus
1:24:50
property so what you can do we can basically call input rep. current Focus that means whenever I click on this
1:24:56
button I I'm basically focusing on this input now this is one a very simple example but this is how you need to
1:25:03
basically do it all right now let's move on to the next one all right so now next one how can use ref can be used to store
1:25:10
mutable values now this is kind of similar example that we have discussed in the previous one so again you can
1:25:15
basically give another example like let's say counter example that there is a button and on click of this I need to
1:25:21
basically store this value in inside a r so what we can do again we can import
1:25:26
use R from react then every time whenever you will do so you'll take a
1:25:32
counter ref for example and then here you take use ref and this is your initial value which is zero and now what
1:25:38
you can do right again I mention right this ref will give you the current property so what we can do we can
1:25:45
basically on click of this we need to increase the count ref by one so we do count rep do current plus one that means
1:25:50
every time I click it will store the uh it it will basically give you the updated count value and that you can
1:25:57
basically store it so this is kind of that example so either you can give this kind of example or the input one is also
1:26:03
really good that we have discussed in the previous one right now let's move on to the next one what is forward R and
1:26:09
when you should use it so forward rape is basically let's say you have some requirement so you need to there are two
1:26:15
components and you need to pass a rape property your R object from one component to another component in that
1:26:21
case you can use the concept of forward rep as the name so forward rep is a function that allows
1:26:27
to pass reps through components to access Dom elements right or child component instances how you can do that
1:26:35
so simply you can see that what we are having right you have a app component here and there you have input ref and
1:26:43
this is simply Ed ref of null so this is your initial value what you have done
1:26:48
you have a component here you notice this is a custom component so this is my my input component and here you're
1:26:53
passing this ra as this input ref what you need to do right you need to use this ra inside this component because in
1:27:01
this component someh you don't have the input element you have the input element in a different component so what you
1:27:06
going to do again I already mentioned right that to use a ra you need to use a r property so here you can basically use
1:27:12
this forward rep function in in this custom component and what this will give this will give you two arguments first
1:27:18
one will be the normal props so let's you are passing a props here that you'll be able to access here and then it will
1:27:23
give you the r property very very important and this R you can basically use here right so what we have done
1:27:30
again I'll recap so first we'll give you the answer that forward ref is a function that allows to pass ref through
1:27:35
components as simple as that keep it simple and then you will give this example that okay I have app component
1:27:41
and then I have another custom component and in this custom component I have input component somehow I need to pass R
1:27:48
to this input component so what we can do from this app component I can pass this r as as a prop not this is not a
1:27:55
prop right this is you are using as a forward R so you'll pass this R here then you wrap this myp put inside this
1:28:01
forward function because this will be a function which will give you two arguments one will be the normal props and one will be the R so this ref you'll
1:28:08
be able to pass it now here now what you can do you can do certain things right in this component also because you are
1:28:13
able to pass this ref from this component from the app component and then you'll be able to access it in a custom component so this is what exactly
1:28:21
forward ref is now let's move on to the next one all right now this is a
1:28:26
important questions I'll say like because you will you can get Theory plus you you will get practical or handson
1:28:33
also because they can ask you okay tell me how you can do forms uh handle forms
1:28:38
and create a very simple input and there will be a button and one click of this button you need to submit the data in
1:28:45
your API call you no need to do the API call in in your interview only but they will see that how you're going to do the
1:28:51
process so what you will do right to give these kind of things I'm again repeating try to give this uh all of
1:28:59
these questions answer using some example it will be much more clear to basically explain to your interviewer
1:29:04
right if your interviewer is not allowing you to write then you can basically tell in a theory way so first
1:29:10
we'll say that okay uh to create or manage forms we need to basically first take our form element right so we need
1:29:18
to wrap all of our uh elements inside form so this will be your first step so first create the jsx structure so you
1:29:24
have a form and then I have a label and then let's say inside this label I have input which will have a type of text
1:29:32
also take a name property here take ID property then you have a onchange this we have already discussed and we have a
1:29:38
value property so now you will take a state which will store the current input unchange value so you have a name set
1:29:46
name which is use state of mty right and then in the on change what you are doing
1:29:51
simply you are basically saving the value in this set name so let's say I have input here and I have a button so
1:29:59
whenever I'm typing something here let's say I'm typing my name you are storing this name suum inside this name value
1:30:05
right and now inside this form you will take a button and the type has to be submit this is very very important now
1:30:12
this all the things that your interviewer will basically see so type is submit now when the type will be
1:30:18
submit whenever in this form you need to take a onsubmit event because whenever I
1:30:24
click on this button I need to get this value suum that I typed and let's I need to pass it in API call right so what you
1:30:31
need to do you need to take a on on submit which will be a method and this will give you event now here you need to
1:30:38
take this event. PR default this is also very important and you can also ask like why you are writing this so this is
1:30:44
every time because this is a form you will click on this button your page will be getting refreshed now to to basically
1:30:50
uh stop that behavior what you are doing you are basic basically preventing that using event. prevent default right and
1:30:57
once you'll do this one now what you can do you can tell your interview that okay now I'll be able to get the name here in
1:31:04
this handle submit and then I'll be able to pass it to API call so this will be the whole process and again I'm
1:31:10
repeating please try to practice this example using by by your own okay create a simple form instead of creating one
1:31:16
input create two input right and create a button and then see if you submit this
1:31:21
button you will be able to access these values on or not so now let's move on to the next
1:31:27
one now okay what are custom Hooks and why do you need them now you can
1:31:33
basically get this one a theory example and then once you will tell the theory part they they can tell you okay now
1:31:40
Implement a simple custom hook something like that so what is custom hooks so custom hooks are basically JavaScript
1:31:46
functions that allow you to reuse the stateful logic across multiple components now what can be proper
1:31:52
example of this let say you are having five components right and each and every
1:32:00
component you have a state and then you need to do a API call every time you'll go from one component
1:32:06
to another component means every time there is a API call that you need to do whenever we we switch from one page to
1:32:12
another page or one component to another component so what you normally do it right so you need to take a use effect
1:32:18
each and every component correct and then you need to do a API call and then you need to store that in your
1:32:24
but how you can basically minimize the effort here so that instead of doing API call every time you will do the API call
1:32:31
in one place using a custom hook and then you'll reuse that in every component so this is what exactly it is
1:32:38
doing that it is basically using reusable stateful logic across multiple components right and what it basically
1:32:45
does without repeating code very very important right and also it promote the code reusability and separation of
1:32:52
conserns now what are are the main uh advantages again the code usability will be more uh then we have the separation
1:32:59
of concerns right and then also cleaner code this is also very very important part that cleaner code because if you're
1:33:05
moving your logic to Common custom hooks you no no no you are no need to write
1:33:11
the same logic in every component right so that means it not only usability will be more but the code will be much more
1:33:17
cleaner and also it will be for other developers it will be easy to understand so this will be a proper uh answer that
1:33:24
what are custom Hooks and why do you need them now in the next couple of videos we'll be couple of uh questions
1:33:30
we'll be learning some two three two hooks which you'll be mostly ask in your interview so let's go to the next one
1:33:37
all right very very important so Implement use use fet custom hook so this is that example let's say you have
1:33:43
multiple components and then every time instead of doing the API call you'll create a custom hook use
1:33:50
page and then you'll be reusing reusing the logic in every component so how
1:33:56
you're going to do that so this is our hook logic right so hook as I already told you what this is Javascript
1:34:02
functions so we give this one name as use fetch now what this will receive
1:34:07
this will receive a URL right this URL will be that from which endpoint you
1:34:12
want to get call the API because from different different components or different different pages uh the URL
1:34:18
will be different right so you'll receive the URL as a input then you'll take a data and a set data which will
1:34:25
set your data and a loading State and these all I'm not repeating again because we have already discussed now in
1:34:32
this uh use effect hook what you're are doing you're taking a use effect sorry use f hook in this custom hook you
1:34:38
taking a use effect and you're doing the API call Simple API call and once that data is done you are basically setting
1:34:44
the data right now the important part is that at the end you need to return the
1:34:50
data and the loading State as a object value now whatever format you are passing let's say you're
1:34:55
passing as object it will be object if array it will be array something like that now the your custom Hook is done so
1:35:02
now let's say from this component I need to use it so how you you can do that so first we'll take cons and this will give
1:35:08
us data and loading right because this is what we are passing here data and loading then you need to call the use Fetch and what you need to pass you need
1:35:14
to pass the URL and simply pass the URL and see the logic how minimized this is
1:35:20
right because you are doing all of these things in this custom hook now this is only for one component now let's say you
1:35:25
are having 50 components so you need to write this one line of line and then you'll be able to get the data this is
1:35:32
the very huge advantage or improvements in your application that you can do right so this is how you can Implement a
1:35:38
use fet custom hooks now let's move on to the next one all right now this is
1:35:44
another one but this also you can get like intermediate level of interviews not very beginner level like Implement
1:35:49
use window resize custom hook this is like whenever you resize your window automatically it will tell the current
1:35:56
width and height right so how we are going to do that again this will be a
1:36:01
function JavaScript function right use window resize and here you are taken your state which which is your window
1:36:07
resize which will be current will be window. inner width and height will be window. inner height now what we are
1:36:15
doing you are taking a use effect which is to handle the window resize events and here you are taking a add event
1:36:21
listener and what you need to do every time resize the window let's say we're resizing this window we're going to call
1:36:27
this function handle resize and whenever I resize that will give us current inner
1:36:33
width and inner height and that we are setting in our state set Windows size here right and once this is done we
1:36:40
basically removing the listener and as simple as that so what will happen every time resize the width and height of your
1:36:46
current window the width and height will change and that will be basically returning here uh the window size now
1:36:53
let's you need to use that in a component so what we can do simply call the use window resize and what this will
1:36:58
give us this will give us width and height and this is coming from this width and height here now whatever
1:37:04
things you can do let's say you need to implement width and height here or let's say you need to implement some custom
1:37:10
CSS so whenever width will be less than 750 you need to make this H1 as red so
1:37:17
that you can simply check that if this withd value is less than 750 I'll make this one red or else it will be black so
1:37:23
this is just to example that this is how you can do so keep your logic in one hook and then you can reuse it in all
1:37:29
the components so now let's move on to the next one all right so next is what
1:37:35
is react router Dom and why it is used now we come into our one of the most
1:37:40
important thing that is routing concept now from this module you can get quite a few things right how you can Implement
1:37:47
routing and what are the libraries that you'll use so first see the simple example like you will tell the uh
1:37:53
normally we use react router Dom they can also ask you what is the latest version so it is version six right so
1:38:01
react ROM is a routing library that built on top of react router package right so what basically does you will be
1:38:07
able to implement various kind of routing uh functionality for example uh moving from one page to another page
1:38:13
then you can Implement Dynamic routing and these things you need to mention right it uh enables Dynamic routing in
1:38:20
web application allowing you to Define routes and navigate to different components without reloading the page so
1:38:27
this will be a very simple definition of react router Dom now let's move on to the next one so now the uh questions can
1:38:34
be very uh like simple one let's say okay now tell me how you can create a very basic route or what are the
1:38:41
component that you'll be using to create a simple route so here the answer will be to create a basic route we need to
1:38:48
use the route component what it takes it takes a Path property that in which path
1:38:54
you want to navigate and then also it will take that okay if I go to let's say SL login page SL login which component I
1:39:02
need to render so this is what exactly we have done so you need to tell that we need to use the route component of rect
1:39:07
router Dom here we need to pass a path that okay I need to go to the/ homepage
1:39:13
and whenever I'll go to the homepage I need to render the home component whenever I'll go to the let's say
1:39:19
register page I need to take a element which will be my register component something like that right so this will
1:39:25
be a very simple example that you will take a route component pass a path and for this path which element you need to
1:39:31
renter as simple as that now let's move on to the next one now they can also ask
1:39:37
you like how to implement basic routing using react router so what we need to do right so first thing is that uh whenever
1:39:45
we want to implement any routing functionality we need to wrap our component or our app component or our
1:39:52
root component inside this browser router so they can ask you what exactly this does see we
1:39:58
remember we have done this context right in the context you have a provider until unless you'll provide uh this provider
1:40:05
in your root component you'll not be able to access so this is what exactly it does until unless you'll wrap your
1:40:11
app component inside browser router you'll not be able to use any of the route features right so that is the
1:40:16
reason the first step will be uh you need to wrap this in your root component so the best place is index.js
1:40:24
file we are doing here but it's better to do in the index.js OR TSX file the
1:40:31
main root file so first we have rap it so we have a browser router and then we need to take this routes component very
1:40:37
very important now don't get confused with this route and routes there is a s after this what this does right in the
1:40:44
previous version version five and less we have the switch component now what this does let's say currently in this
1:40:52
routes component will basically help you to switch from one page to another page the reason is let's say currently we're
1:40:57
in the homepage and there is a button login button whenever you click on this
1:41:02
button you need to navigate to the login page so that means from homepage you need to change the path to login page
1:41:09
right so this what routes component will do this will help you to switch from one
1:41:14
page to another page and inside this routes you need to take all the route that you will be having so let's say in
1:41:21
your uh application you have 50 routes so inside this route component you'll be creating 50 route component like this
1:41:28
individual one two one for home one for login one for register one for something else so like that and for each and every
1:41:35
route you have again a path and the element so this we have already discussed here right so this is how you
1:41:41
need to implement very simple one so if you do this and then let's say you want to go to the homepage then you'll see
1:41:47
that this home component will be getting rendered right so these all the steps you need to explain in your interview
1:41:52
and if you're able to explain like this more than enough right you don't need to do anything else now let's move on to
1:41:59
the next one how to create link to another route means how you can go from
1:42:04
one page to another page using a link let's say you have a nabar component so this is your web page and you have a
1:42:10
abar and here you have a home and here you a login right and whenever you click on this home link you you'll be in the
1:42:17
home page whenever you can click on the login link you will be on the login to
1:42:22
implement this first you need to import link component from react router Dom and
1:42:28
then you need to wrap this home this home here inside this link and what it will take it will take a two property
1:42:35
right two means which path in which path I want to navigate so when I'll click on
1:42:40
this home I want to navigate to slome page when I'll click on this about I need to go to the slab page if I have a
1:42:46
login page if I go to SL login in this two means I'll go to the login page some
1:42:53
like that so the answer will be import the log link component from RE router Dom and then use this link component and
1:42:59
then pass a two property and in these two property you need to pass the path name that you want to navigate to as
1:43:04
simple as that right now let's move on to the next one how do you use URL
1:43:12
parameters or dynamic routing in react router now what exactly is dynamic routing is the question might come so
1:43:17
you will give like this example that okay let's say I'm creating a e-commerce page and I have five five
1:43:25
products whenever I click each and every products I need to go to a Details page right so this is your Details page so if
1:43:32
I click on product one I need to show product one if I click on product two I need to click this I need to show
1:43:37
product two if I click on product three I need to see product three so that means every time this data will change
1:43:44
so somehow you need a dynamic routing so how you can do let's say your this page
1:43:50
that you are having in this page you are have a product list your route name now whenever you
1:43:57
click on this you need to go to the details page and The Details page is something like this slash list slash for
1:44:04
product one this will be one for product two this will change to one to two I hope you're getting for product three
1:44:10
this will be from two to three for four this will be four right so that means this value is a dynamic value so how you
1:44:17
are going to do that first you need to create the route now see in the previous one we discussed right how you can
1:44:22
create this route here path you need to take the path and you need to take the
1:44:28
element so here again you need to take a path the only difference is that for the dynamic value so this is the dynamic
1:44:34
value you need to take this colon simple as that this colon means you are telling this route that okay this route is now a
1:44:41
dynamic route okay so this is how you need to do it and here you need to again pass the
1:44:47
element now to access this value to get this value from your url you need to use
1:44:53
this use param Hook from use rout react router so what this param will give you
1:44:58
this will give you this user ID value so you can see that you'll be able to get this user ID and then you'll be able to
1:45:03
render it so for example you are going to a user of ID 100 so here you'll be getting 100 for uh you are getting
1:45:10
another user for 100 150 you'll be getting 150 so this will be your Dynamic value and to do that you need to take
1:45:16
this coron two colon and then you need to pass the something like user ID or whatever you'll pass all right so this
1:45:22
is how you need to create a dynamic routing now let's move on to the next one how you can perform a redirect in a
1:45:30
rout now this uh first give a simple example that okay we can use navigate component to perform a redirect right so
1:45:37
again the simple example is that let's say first you need to import navigate from RE and you have a login page right
1:45:44
so let's say if the user is not logged in you need to go to the homepage if the user is loging then only will be in the
1:45:51
login page or something uh in the uh login page or any whatever so here what we have done we are checking that is
1:45:57
logged in right so if this is the user is logged in what we are doing I told
1:46:02
you opposite so if the user is logged in we are navigating the user to the homepage if the user is not logged in
1:46:09
the user will be in the login page but this is not about the question the question is how you can navigate so you need to use this navigate component
1:46:16
right and then you need to pass the two property that which path you want to go so if the user is logged in I want to go
1:46:21
to the homepage so you need to take the component and pass the two and then you pass the path name as simple as that all
1:46:27
right now let's move on to the next one what is routes component in re
1:46:33
router I think we already discussed this routes right that this route is basically uh the it will basically check
1:46:40
or basically help you to switch from one page to another page how it will do it will check the matching route is rendered what is this matching route is
1:46:47
rendered for example it will check that for this route the path is home so now
1:46:52
if in the browser if I search for slome so it will match this route with this
1:46:57
route and it will check okay there is a match from this home and home so I need to render the home element I hope you're
1:47:03
getting if you search for SL about so again it will check okay there is a
1:47:08
match this about page means user want to go to the about page so it will check okay which path is the about so it will
1:47:14
check this one so it will render the about component all right so this will help you to switch from one page to
1:47:19
another page it will check that which matching route I need to rendered all right so this will be the routes
1:47:25
component uses in R router Dom now let's move on to the next one now another very
1:47:31
very important question that how you can handle uh nested routes in react rout so
1:47:36
what exactly mean by nested routes I'll give you a very simple example let's say uh you are having a
1:47:43
page and here let's see this example only that you are having a dashboard
1:47:48
page and in this dashboard page let's say you are having a common part which is your home home or dashboard so this
1:47:55
part this part will be common for all the pages only this part will change here so
1:48:02
let's say you will go to SL dashboard SL login so this part will always be same
1:48:08
but here we need to show the login page if you go to/ dasboard / profile we need to show here the profile page if you go
1:48:15
to/ dasboard SL settings we need to show the settings page so that means we need to somehow create a nested component
1:48:22
here but every time this part will be always common so let's see how we are going to do that first again you need to
1:48:28
take the routes which is to switch and then you need to take a route component
1:48:33
here which is your home route dashboard and you'll tell that okay I need to
1:48:38
render the dashboard element and inside this route you have all the nested
1:48:44
routes so inside dashboard I can have a profile page I can have a settings page I can have 10 other pages right and how
1:48:51
you're going to render in this dashboard component very very important you see this part here so this part is this
1:48:57
common part so this is the common part means every time you'll go to/ dashboard
1:49:03
route this dashboard this part will always be getting lended so how you'll be able to switch then this this part
1:49:09
I'm talking this part so this you need to switch using this Outlet component whenever you'll pass this Outlet react
1:49:16
router do will check okay there is some nested routes and it will come here and check okay yes there is two nested
1:49:21
routes so that means if I go to/ dashboard slash profile I need to render the profile page if I go to/ dashboard
1:49:28
SL settings I need to render the settings page to nested this you need to use this Outlet component I hope you're
1:49:34
getting and this part will be always common so this is this part so now let's move on to the next one now this is a
1:49:42
very simple one that how you can handle 4 not4 Pages or not F page let's you are going a ABCD page and this page doesn't
1:49:49
exist so you'll show user that okay this page doesn't EX something like that or not found page and to do that it is very
1:49:56
very simple first create a component let's say I created a not found component and I'm getting 4 not4 not
1:50:02
found and to map this what you can do right you need to pass the element not found and in this path you need to pass
1:50:08
this star this is the important one if you pass star here so that means react router will understand okay this route
1:50:14
is is is a not found Route so whenever us try to go to a route which doesn't
1:50:20
exist it will render this not found page right and the main trick part is you need to pass the path if you don't pass
1:50:27
the path as star it will not work right so this is how you need to implement not found page in react router Dom now let's
1:50:34
move on to the next one all right how do you programmatically navigate using react router Dom so what exactly mean by
1:50:40
that let's say you having two buttons on click of one button you need to go to SL homepage on click of one
1:50:47
button you need to go to the/ login page and then there is one more button here in this case you need to to do some
1:50:53
logic some API call once you'll get the API response then only you need to navigate so that means this will be
1:50:59
programmatically you need to navigate how you can do that you need to use this use navigate Hook from di router I'm
1:51:06
going little fast but I'm again repeating please Implement all of these
1:51:11
handson means don't see this video and then you'll say okay I'll be able to do it if you're interviewer ask you to do a
1:51:18
example then it will be very tricky because I know from my own experience that even if I know everything in
1:51:24
interview the situation will be completely different some easy things also will not be able to do it so I'm
1:51:29
suggesting please try to implement all of this by your own see this example and then write it and see whether you are
1:51:35
able to do it or not and also see how much time you are taking so first you need to take use
1:51:41
navigate hook and then we take the use navigate which is navigate and then simply let's say I have a button and on
1:51:47
click of this button I need to go to the homepage call this navigate and inside this navigate you need to pass that
1:51:53
which path you want to navigate so this will be navigate and then here you need to give the path so whatever path you
1:51:59
will provide here it will go to the that page so this is how you need to na programmatically navigate so you need to
1:52:05
use this use navigate custom hook all right now let's move on to the next one all right so next one explain use
1:52:12
callback hook with example now there are uh two hooks that we need to discuss that is use call back and use memo both
1:52:18
are used for memorization and also performance Improvement so the example or definition will be that use callback
1:52:24
H used to memorize callback function right this means the function provided to the use callback will only recreated
1:52:31
or only run if one of its dependency will change right and if after this they
1:52:37
will ask you to give a examples of what we can do right simply so let's say uh
1:52:43
we have a component here and then we have a child component right so what we are doing right so you can see that in
1:52:49
this child component I have button and where I need to do some kind of expensive uh calculation right so what
1:52:56
we can do because this child component I'm using as a child in this parent component so I can pass a call back as a
1:53:03
pro which will be my memorized call back this memorized call back will be a function which will be wrapped inside
1:53:09
use callback and here we are basically passing this expensive computation as a dependency now this is uh not has to be
1:53:16
only getting from props this can be any dependency so what exactly I mean by that whenever you call this memorized
1:53:23
call back from this component now because here we are passing as a call back this component will not rerender
1:53:30
until unless the call back changes so this call back is this memorized call back now when this will change whenever
1:53:36
there is a change in this expensive computation prop value right so this is what what exactly we are telling that if
1:53:42
it will only getting recreated if one of its dependency will change one more very important Point whenever you'll be
1:53:48
passing a call back you need to also wrap your my child component inside the
1:53:53
re react memo component right react. memo so this also we going to see because if you mention this point you
1:54:00
can get a counter question okay now tell me what exactly react memo is so this we are also going to discuss but first try
1:54:06
to understand the use callback so use callback is basically a hook that used to memorize callback function and you'll
1:54:12
pass a dependency Whenever there is a change in the dependency that time this memorize will this callback function
1:54:18
will be getting rendered now let's move on to the next one see again explain use
1:54:23
memo now both are almost similar but not so like there are some differences
1:54:29
differences is that as the name suggest callback basically memorize a callback function me use memo memorize a value so
1:54:37
that is the only difference see use memo Hook is used to memorize expensive
1:54:42
expensive calculation so that they're not recalculated on every render right it
1:54:48
takes a function to compute a value this is the important right and array of dependency so if any
1:54:55
of the dependency will change then only it will recompute or recalculate the value or else it will not see uh this
1:55:03
example very simple one first you need to import from react now let's say we
1:55:09
are doing some uh expansive calculation here right what I want to do right for
1:55:16
example here you notice one thing we have one more State count and set count
1:55:21
and there is a Buton button every time clicking on this button this count value I'm increasing from 0 to 1 2 3 and four
1:55:28
in normal use case what will happen right if you don't create this part here let's say this part is not exist every
1:55:36
time you click on this button the state is getting changed now what will happen if the state changes in react if there
1:55:42
is a change in state the component will rerender if the component will reender every time you're rendering this part
1:55:49
this computation value function and this is very important every time you're rendering although you can see there is
1:55:56
no changes here you are only changing the count value but still these values this function is getting rendered not
1:56:02
function this value is getting rendered so how you can stop this so you can wrap
1:56:07
this function inside use memo right and you will tell that okay here we are
1:56:13
passing this count as a dependency but that is fine it's not about the count let's say you have some different value
1:56:18
so you'll tell that okay whatever dependenc I'll pass here inside this this expensive value will be
1:56:25
recalculated whenever there is a change in this dependency as simple as that if there is no change in in this dependency
1:56:31
this function will not be getting called so that is the main difference from use call back and use memo use callback is
1:56:39
used to memorize call function on the other side use memo is used to memorize a value and in both the cases you need
1:56:46
to pass a dependency array Whenever there is a change in the dependency and based on that it will recalculate now
1:56:51
let's move on to the to the next one now again explain react memo with example so what exactly react memo so react memo is
1:56:58
a hocc component higher order component that memorize the result of a component right what it does again it use for uh
1:57:05
like performance Improvement so that it will not rerender the component until unless the props are getting changed
1:57:12
right so what we going to see previous example you have seen right here we have a count value and we have a button very
1:57:18
simple one and we are increasing the count by one now I have a child component and in this child component if
1:57:24
you notice this my component is the child here I'm passing this count as a prop and what I have done this my
1:57:31
component I wrap inside this memo right this is a higher order component when I'll wrap this in this memo this
1:57:38
component will understand okay now this component will only render if this value
1:57:43
prop will change or else not and this value prop is this count value that means every time we click on this button
1:57:49
this component will be getting rendered but let's say you are having some different state also here if those
1:57:55
States will change this component will not get rendered the reason is because this value will not be getting changed
1:58:00
right so that means whenever we wrap this inside memo it will check that if any of the props are getting changed
1:58:06
then only this component will rendered here this one so this is the main advantage of react. memo all right now
1:58:13
let's move on to the next one all right explain the reconciliation process in
1:58:19
react and how it works see here this process is basically to update the Dom
1:58:24
efficiency if you remember we have the concept of virtual Dom so what basically does react keep a track of the virtual
1:58:30
Dom and the real Dom and it will compare using some algorithm but it checks that if there is a change in that virtual Dom
1:58:36
then only those part will be getting updated in the real d right so what basically is that this process is
1:58:42
comparing so this is the process that is called the reconcilation that it compares the new virtual Dom with the
1:58:47
previous one and determine that the minimum number of changes needed to do to update the actual do so here you can
1:58:54
see that we are having some list of items so we have item 1 2 3 let's say four now whenever I'll click on this
1:59:02
button let's say I'm adding a new item so when I'll add a new item right this new item only will be getting added in
1:59:08
our previous Dom because this will be your new virtual Dom where you have a new item so it will compare that okay in
1:59:14
the previous Dom I have only four items but in the new one I have five items so this is the new that is getting added so
1:59:21
it will only add this part in our virtual sorry in our main Dom on the or basically the real Dom and this
1:59:27
comparing process is basically called the reconciliation process now let's move on to the next one what are pure
1:59:34
components now these pure components are basically based on the class based components in react right so in normal
1:59:40
functional component you use memo in class based component you use the pure component so what basically is does that
1:59:47
pure component is a base class in reacts that implement the sued component updates so this is the same logic that
1:59:54
if uh you want to check that okay if there are any changes in my prop then only I want to render this component or
2:00:00
else not and to implement this what you can do so what it helps it helps to unnecessary reender right so what it
2:00:08
does basically first you need to create a parent component and in this parent component you are basically managing
2:00:13
some State and then you are calling out child component right this child component you need to extend with pure
2:00:20
component so this pure component you need to import from react if you do that then what will happen react will check
2:00:26
that okay if there is a change in this prop then only I will render this component or else not right so this is
2:00:32
what is the pure component is so for functional component you can use memo for class Bas component you can use the
2:00:37
pure components now let's move on to the next one now what is higher order
2:00:42
component explain with example see higher order component is similar logic as higher order function so higher order
2:00:49
component is a function that takes another compon and returns a new component with some
2:00:54
extra added functionality and this feature is basically used to reusing component logic right so how it will
2:01:01
work so let's say here you can see that I have a simple my component which is
2:01:06
component is loaded what I've done I created a higher order component here which received the component as a input
2:01:13
because I already told you right that higher order component takes a component and returns a new component and this component if I call here you can see I'm
2:01:20
calling this with loading and then I'm passing the my component this component as a input so this component it will
2:01:26
receive here then it is returning a new component see class with loading extend
2:01:31
react. component and here what you are doing the simple logic is that you are doing certain things and then you
2:01:36
returning a new component here and what will happen this is for one example let's say the same logic this part here
2:01:43
this part you need to do it in 100 component so instead of doing it in multiple places what you can do right
2:01:49
every time whatever component you will be creating you wrap that component inside this hocc or higher order
2:01:55
component so what will what will be the advantage Advantage is that you are not writing this logic every time 100 time
2:02:00
you're reusing this logic and you are using this as a part of a higher order component so that is the example or the
2:02:07
definition of hocc and react now let's move on to the next one all right everyone so now we uh comes into another
2:02:14
new topic and that is called Redux so we have covered the context API now we have
2:02:20
also alternative as Redux or Redux toolkit so what is Redux and explain the
2:02:26
core principle see Redux is basically State Management library right and that is the very important part is that this
2:02:32
is predictable State container for JavaScript apps this is not for only react you can use Redux in others also
2:02:39
like angular view so Redux acts as a centralized store means in one place you
2:02:45
have all the store and then you just consume it like in your application so what are the advantages that single
2:02:51
source of TR Roo the single source of tro is basically nothing but that all the component state is stored in a
2:02:58
single object simple as that it's read only that means you can only change the state to emit accent that we are going
2:03:05
to see in the next videos but you will be explaining all of these and changes will be made on pure functions right
2:03:11
pure function is means that takes the previous state and action and return the next state so these three are the main
2:03:18
uh like advantages and what exactly basically Redux is now let's see all of this with simple example so now next is
2:03:25
what are Accents in Redux explain with example see accents are plain JavaScript
2:03:30
objects that describes that what happened in the application for example I have a button and I need to click on
2:03:37
this button and I need to decrement the count by one so whenever I click here I need to dispatch accent right to my
2:03:44
Redux store so you have react and your Redux so this is your Redux and this is your react so you have a button in Redux
2:03:49
right react right and you need to tell that okay whenever I'll click on this button I need to go to Redux store and I
2:03:55
need to dispatch acction and I need to inform my Redux that okay whenever I'll click on this button in decrement the
2:04:01
count by one so that is what exactly accents are accents are simple JavaScript so you can see that this is a
2:04:06
increment accents that I have created which is basically dispatching a type if you remember we have done this one in
2:04:12
use reducers also right we are dispatching a type and here this type is very very important this is mandatory
2:04:18
because this type will basically tell what exactly this access is doing for this one we are doing a increment for
2:04:24
this one we are doing a decrement for other we are doing something else so type has to be there so this is exactly
2:04:30
what acction in Redux are now let's move on to the next one explain reducers in
2:04:37
Redux with a example so reducers are basically a pure function right which takes the current state and acction and
2:04:44
Returns the updated State based on the accent type based on the accent type remember we have dispatch accent right
2:04:51
and here having a type and in this type we're basically telling that okay in this reducer that I have accent. type
2:04:57
this is my type of increment and if this is increment return me the updated state with increment if this is a decrement
2:05:05
return me the updated state with decrement so this is what exactly redu sir and you need to basically mention
2:05:10
that pure functions that it takes the current state and action and this action will have a type this type will
2:05:18
basically tell that which thing I need to do and based on that it will return you the new state or the updated State
2:05:24
now let's move on to the next one what is the role of Redux store or how you can create a Redux store right see just
2:05:32
like in the context we have a provider right and then you wrapping that in your app component so here you're having the
2:05:37
app similarly when you'll create a Redux store this store holds the whole state
2:05:43
tree of your application and you need to wrap it so that we are going to see but you need to basically explain that the
2:05:49
store Redux store uh holds the the all the state tree of your application it
2:05:54
allows to access to the state state VI either you can use G state or you can dispatch acction using dispatch or
2:06:01
basically register using subscribe right so here you can see that we are creating a create store and we are passing the
2:06:07
reducer function which basically nothing but returns updated State and then you can use something like get state or you
2:06:13
can also dispatch it and then you'll be getting the updated state so for example first time State count is zero so you're
2:06:20
getting count is z one then you are dispatching a type of increment so when you dispatch a type of increment it will
2:06:26
go here it will increase the count by one and next time when you'll do so count is now one I hope you're getting
2:06:32
right but the from the question perspective the answer will be store is basically holds all the application
2:06:38
state in your Redux store now let's move on to the next one all right how to
2:06:44
connect react with redu store using connect now they can specifically mention that how you can do using
2:06:49
connect because there are other ways also we can do that so if they ask you how you can do using connect so what you need to do that
2:06:55
connect is basically a function first you need to import it from react Redux package so react Redux package will give
2:07:03
you the capability to connect your react with your Redux store because see
2:07:08
Redux is a completely different thing you need to connect both so this package will help you to connect both react and
2:07:15
Redux then you need to First import the connect function and here what you need to do right so first let's say you you
2:07:21
are creating two things one is your map state to props so this map state to props will give you the updated state
2:07:27
from your Redux store and this map dispatch to props is nothing but the dispatching the accent to your Redux
2:07:33
store and then what you need to do right you need to basically map all of this state to props and map dispat to props
2:07:40
inside this connect function so you can see that we take our connect function we pass map state to props and map dispat
2:07:45
to props and then we wrap this in our component so this component now what we have done so we basically tell that okay
2:07:51
this this is our component now we are connecting this component with a Redux store and these all the things that we
2:07:57
need we need the count value and also we are dispatching accent so this accent is nothing but this increment right so this
2:08:03
is what exactly you need to do so these things you don't need to give example because they will not tell you to okay
2:08:09
tell me examp with example sometimes sometimes they will say but first they will see the theory so in the theory
2:08:15
basically you need to tell that connect is a function that connect your react component with your Redux store right it
2:08:21
is basically Maps your state so this is the state and also the accent using map dispatch to Accents so this will be your
2:08:28
answer now let's move on to the next one now comes the very very important part because this is what we currently used
2:08:35
that what exactly use selector hookies and use dispatch hookies right see if
2:08:41
you don't use this connect nowadays I think no one uses because most of us we use use selector and use dispatch what
2:08:48
basically this does right so use dispatch is basically dispatch action as
2:08:54
simple as that you selector is give you the updated state from Redux store so let's say you have a Redux store right
2:08:59
and you have a count value which is one you need to get this value from Redux and you need to render in your react so
2:09:06
you need to get this value somehow in your react component right so use reducer basically will help you to get
2:09:12
this from your Redux store simple then you have used dispatch dispatch is
2:09:17
nothing but let's say you have a button here in this react and you need to dispatch access to your Redux store and here you can use this use dispatch
2:09:24
simple very simple so first you need to import use dispatch take this dispatch
2:09:29
and then on click you can see we are dispatching a increment action this is our action and what is this action we
2:09:36
have already discussed this action is with a type right so you're dispatching
2:09:42
action and using use selector you'll be able to get the updated State means it is something like this let's say you
2:09:48
have a button you are dispatching accent right it will do certain operation it is giving you the updated State and then
2:09:54
you're getting the updated State back something like that again you click this will become two because they're increasing the count again you dispatch
2:10:01
this will become three right so these two hooks are very very important one is use selector and one is use dispatch now
2:10:07
let's move on to the next one all right what is Redux toolkit and this is what
2:10:12
currently we are using so Redux toolkit is basically the official tool set for your Redux development So currently we
2:10:19
don't use separate Redux and those things we normally use Redux toolkit right because it gives you some very
2:10:24
simplified store setup some reducer boiler plate and also you can use some uh tools like re create slice create a
2:10:31
sing Tong and those things right for API calls and everything so this will be the definition of Redux toolkit now from
2:10:37
here you might get some of the things some queries that we are going to see so the first thing you'll be getting how
2:10:43
you can configure Global story in your Redux toolit very very important now these things you might get that means
2:10:50
how you can create a store again I'm repeating that we have discussed that in context we need to
2:10:55
wrap our provider inside app right similarly when you use a redu you need to wrap your app component inside store
2:11:02
something like this this is your app component and then you need to wrap inside store so this is
2:11:09
your Global store and inside Global store you will be having your app component so how you can do that so basically you will tell that okay I will
2:11:16
use configure store method from Redux toolkit and this configure store will give us will help us to create our main
2:11:23
Global store so here inside this configur store we need to pass the reducer all the reducers very very
2:11:29
important and this is mandatory if you don't pass any reducer it will not work so inside this configured store you pass
2:11:34
the reducer and this will give you the global store and then what you can do right you need to use a component that
2:11:41
is called provider so that we are going to see later but to answer this question that how you can configure store answer
2:11:47
will be very simple we need to import configured store from Redux toolkit and this configure store in this this will
2:11:53
be a method where we need to pass all the reducer and this will create our Global store that's it now let's move on
2:11:59
to the next one now what is create slice in dedu to get explained with an example
2:12:05
now see this kind kind of things is only help you if you already worked in Redux
2:12:11
if you're coming here for the first time and you are seeing all of this clear slice you'll not be able to understand so that's why I already mentioned in the
2:12:17
first time that this video will be for those the who have already worked all of
2:12:22
this and this is just to give you or basically you'll be able to revision purposes let's say you interview in two days you'll be able to check all of this
2:12:29
so that you'll be able to answer so what exactly create slice is Right create slice is a function that generate your
2:12:36
acction creators accent types and also the reducers so how you can do that so create slice will be first we need to
2:12:42
import from Redux toolkit this will be a method which will take a name so name is
2:12:47
nothing but your identifier so this is your counter slice it will take a initial State and it will take the
2:12:53
reducer in this reducer you will be having the accent Creator so these all your accent creators this is also accent
2:13:01
creators so this is your increment accent this is your decrement accent and then at the end what we need to do we
2:13:07
need to export this accents so increment and decrement so that we will be able to
2:13:13
call all of these from our react app and at the end you need to export this reducer once you'll export this reducer
2:13:20
what you need to do if if I go back you need to pass this reducer here so here you'll pass counter will be your counter
2:13:27
reducer so once you pass this reducer then only you'll be able to access it so this is what exactly create slice does
2:13:35
now let's move on to the next one all right so now we'll come into another section which is very very important so
2:13:42
here actually you might get this question that tell me about control components in react and uncontrolled
2:13:48
components what is the difference and give me one simple example all right so so here you need to basically tell the
2:13:54
exact definition so control components are components where the form data very
2:14:00
very important is handled by react State it's very important actually right react
2:14:06
State means let's say you have here see this we have input and then we are take
2:14:12
managing this input value using what using a state so this is what exactly we
2:14:17
are telling that form data is handled by react state the input value is always
2:14:23
driven by react state so here we have a state that we are managing here so this is what control component is what is
2:14:29
uncontrolled components move on to the next one uncontrolled components are react component where form data is
2:14:35
handled by Dom itself very very important you might get this question the input data is not given by react
2:14:42
state so if I go to the previous one right here you can see that we have a state and then based on that we are managing the input value but here what
2:14:49
we have done we take a input inut ref or basically you're managing using ref using Dom and then we have pass this
2:14:55
input ref in this ref and then we how we'll be getting the value so here you'll be getting the value from what
2:15:01
from your react State here you'll be getting the value from input r. current do value so this is the difference that
2:15:08
control components where the form data will be handled by react State whereas
2:15:13
uncontrol components the form data will be handled by Dom itself so you need to take ref and from there will be from the
2:15:20
current property you'll be getting the value so this is the difference between control components and uncontrol
2:15:25
components now let's move on to the next one all right so next how do you optimize performance in react
2:15:31
application this is also extremely important now here you don't need to write any code and everything you need to basically mention all the points and
2:15:38
whatever points you'll mention from there you might get some counter example or question so here first thing is that
2:15:44
we can use some me uh hooks like use memo use callback to memorize expansive calculation we can use component update
2:15:52
or we can also use re memo or pure components that we have already discussed we can also do something like
2:15:58
code splitting and lazy loading so these all the things that you can basically mention now here once you mention all of
2:16:04
these they can ask you can now you mention use memo and use callback okay tell me what exactly those are how you
2:16:09
can do how you can use react. memo component how to implement code splitting or lazy loading something like
2:16:15
that but to give this one in a very short answer these are the points that you can mention now let's move move on
2:16:21
to the next one what is code splitting in react again I told you right that either you can get like tell me what is
2:16:27
how to optimize performance or you can get those questions separately that tell me quote splitting and react in a very
2:16:33
simple example because in interview will not get like you need to implement code splitting from scratch right they will
2:16:39
ask you 20 Questions 10 questions and out of which one of them will be something like this so you will tell
2:16:45
that okay code splitting is a feature that allow us to split your code in various bundles right and which can be
2:16:52
loaded on Demand right and what how you can do that so simply you need to import this
2:16:59
lazy and also you need to import the suspense from react then this lazy will
2:17:04
be you can see we are dynamically importing this home and the about component right just pass instead of
2:17:10
passing it here we are lazily basically importing all of this component and then this we are passing in your route so
2:17:17
this is how you need to basically do that and also we are WRA this switch component or the routes component that
2:17:23
we are having inside suspense and suspense is basically give you the fallback so if anything goes wrong then
2:17:29
it will basically show you the fallback data for now so this is how you can do that so UT lazy suspense and then lazily
2:17:36
import the components each and every individual components and then wrap your uh content or components inside suspense
2:17:42
and pass a fallback component so inside this fallback you can pass any other custom component also now let's move on
2:17:49
to the next one what are render props in react Give an example render props is
2:17:56
basically a technique to sharing code between react component using a prop which whose value is a function right
2:18:02
and this function will return a react element what exactly is that so here I
2:18:07
have a app component and I have a my component which is a child component what we are doing right we are passing a
2:18:13
render Prof here which is a function returning a jsx right so this is render
2:18:19
Prof and passing a function which is a jsx this I'll be receiving here and simply call this method so this will
2:18:25
render this jsx in your browser so that means from definition perspective it
2:18:31
will be it is a technique for sharing code between react components whose value will be a function all right now
2:18:38
let's move on to the next one what are portals in react now these you get very rare these kind of questions but
2:18:44
sometime you'll get so that's the reason I included see portals provide a way to
2:18:50
render a children into a Dom node that exists outside of your Dom hierarchy so you have a real Dom virtual Dom right so
2:18:56
let's say your app component or root component what will happen if you use portal this portal is basically will
2:19:03
render that Dom outside of that Dom tree right of the parent component or basically the root component and where
2:19:10
it is helpful it is helpful to implement for models tool tip overlay these kind
2:19:15
of things so this you can mention and you can also see the example how we are doing this we have a state then there is
2:19:23
a button which is opening a model and we have a model component right this is the model component and here we're passing
2:19:30
this e open as a prop and then we are receiving this e open so you're checking
2:19:36
if e open is false we'll render nothing or else we'll create a portal right so
2:19:41
react Dom do create portal we need to use and then we are basically telling that create this portal and append this
2:19:48
in our document. body which will outside of your root component so this is how you can do that right and this is very
2:19:55
very helpful not very very helpful I'll say like you can use it for models tool tip and some overlay something like that
2:20:02
and this will be how you need to do that so now let's move on to the next one how do you implement lazy loading in react I
2:20:08
think this also you have discussed in that part that lazy loading can be implemented using combination of react.
2:20:14
lazy and suspense what it basically does it basically load the components on
2:20:19
demand and it improves the performance simple as that so I think we already done that we need to import lazy
2:20:26
suspense use the lazy import the component dynamically and then pass this inside suspense and pass a fallback
2:20:33
property fallback you need to pass because if something goes wrong it will render that fall back component till
2:20:39
that so this is how you need to implement lazy loading in react now let's move on to the next one now we are
2:20:45
going to discuss some of the typ skip related things because if your interview or reement is typescript they can also
2:20:52
ask you some typescript or some testing related things also those two things we need to check all right first how do you
2:20:59
define props in a functional component very very simple right whenever typescript means you need to Define the
2:21:05
types so you create a functional component you need to basically tell them okay I have a functional component
2:21:11
and this is my props so these props I'll be receiving and these props is nothing but the interface and here you need to
2:21:17
pass all the properties that what are the props you think that this component will receive from your parent component
2:21:23
so you created the props using interface you pass it in this component and then you'll be able to use it see these all
2:21:29
the things are not very like very tricky if already if you already worked in typescript this will be very very simple
2:21:36
still I thought it will be better to mention all of this point also now let's move on to the next one how do you use
2:21:43
us hook with typescript so again these are very simple right if you're using US
2:21:48
state then you need to basically Define the type here so for example if your initial value is zero which is a number
2:21:55
you'll pass a number if this is false you will pass a Boolean here if this is a string you'll pass a string here
2:22:02
something like that so you need to basically tell the type so you can Define the type of State variable by us
2:22:08
in the UST generic so you're basically typing here right give the type in this generic so this is how you need to use
2:22:14
Us St hook with typescript let's move on to the next one how do you type
2:22:21
even handlers in react with typescript again first you need to take the use state in the general we mention that
2:22:28
okay this is the type of string so that is the reason taken string then I have a input where I have a handle change now
2:22:34
this is very important here in normal JavaScript you need to take only the event but you don't need to specify the
2:22:40
type but here you need to uh specifically tell that okay this is a change event for example and this is a
2:22:46
HTML input element this is very important if this is text area you need tell this is a text area this is Select
2:22:52
you have to mention this will be a HTML select element so this is how what you need to mention if you don't mention
2:22:58
you'll get error and don't tell in interview that I will use any type any type is not recommended to use you need
2:23:04
to basically tell that okay whatever components I have used let's say if it's a input I need to basically tell this is
2:23:09
a input element if you just select it will be select something like that so this is how you need to basically type
2:23:15
your even handlers and react with typescript let's move on to the next one
2:23:20
how do you handle optional props in D components with typescript this is very important like this is a typescript uh
2:23:28
like concept to handle anything optional you need to use this question mark If there is a question mark means this is
2:23:34
optional property you might get you might not get so this is what we have done we have a react. fc means
2:23:39
functional component we have a props and here we have a title which is a string and subtitle and there is a question
2:23:45
mark here that means this subtitle is a optional property either you can receive re it here or you cannot receive it so
2:23:52
this is what you need to mention that you can use this question mark operator to tell the to tell typescript that this
2:23:59
property is optional now let's move on to the next one how do you use use
2:24:05
reducer hook with typescript now again this is uh like you need to basically give the type everywhere right so for
2:24:11
example we have a state we have dispatch reduce an initial state so in the initial state if you notice I created a
2:24:18
interface which is my state interface and here I'm mentioning that my I will have a count the property of count will
2:24:25
be number so this is the first step let's see you have one more let's say you have a text which will be string you
2:24:30
need to mention then in your reducer we have a state and action so for each and
2:24:36
every state we have a type so for the state we have a state interface for accent we have a type interface right
2:24:43
because accent can have a type here so you need to mention the type can be either increment or decrement let's say
2:24:48
you have some more you will give all the this or this or this something like that so type can be either increment or
2:24:55
decrement and you need to specify this accent here right and what it will return it will return the state what is
2:25:01
the state again this is your interface so this is how you need to basically type your use reducer hook in typescript
2:25:09
let's move on to the next one how do you type context API in react
2:25:14
with typescript this is also like these all are the same things I just thought
2:25:19
that it will be better to mention so first thing is that when you create a context right we have a context which is create context you need to basically
2:25:26
pass the context type context value which is a interface this will have a
2:25:31
count which will be a number and this will have a increment which will be a method so this is what I mentioned here
2:25:37
correct then I have a account provider which will be a functional component it will receive a children children can be
2:25:44
of react node so this I mentioned that children it will receive which will be react node as simple as that right and
2:25:50
this is what exactly you need to type whenever you create a context you need to give the type of context and whenever
2:25:55
you create a provider you need to basically give that what kind of props or children it will receive and that's
2:26:01
it so this is what you need to mention in your interview also and this will be more than enough now let's move to the
2:26:06
next one okay now we come into very important uh thing and that is called
2:26:12
testing so test cases they can ask you some questions like okay tell me how you
2:26:17
can write test in your current company or do you have any idea on what are the things that we can use so you'll
2:26:24
basically tell that okay for testing react apps we can use gist or we can use
2:26:29
RTL RTL is react testing Library so just is basically testing framework that is created by and maintained by Facebook
2:26:36
right so they can basically tell you that how you can write a simple test in
2:26:41
uh gist so what you need to metion that okay test will start with this test keyword or we can also use it keyword it
2:26:49
okay so each and every test or it means this is a test block so here first thing
2:26:55
you need to give a description that what exactly this test is doing so here we are adding two items and we checking if
2:27:01
1 + 2 is three or not so this will be your description and then it will give a call back method so in this call back
2:27:08
method you need to give write all your logic so this is exactly how you need to mention that inside this call back I
2:27:15
will have expect that I'm expecting 1 + 2 to B3 now this is not the only thing
2:27:21
you have thousand of logic that you can write but I'm giving one simple example that how you can write a test case so
2:27:27
you need to start with test keyword or you can use it keyword you need to give a description it will have a call back
2:27:33
and inside this call back you need to basically write all the Logics which exist of all the matches and everything
2:27:38
that you can do so this is what will be the answer for this particular question let's move on to the next
2:27:45
one all right how do you render a component for testing using react
2:27:50
testing library because whenever you test a component first you need to render that component right so to render
2:27:56
using react testing Library you need to use this render method so first you'll import this render method from react
2:28:01
testing library and then again you'll do the test keyword and you'll specify the description that I'm testing the
2:28:08
component whether it is rendering or not and it will take a call back method and here you just have to pass render which
2:28:14
is this method and you need to pass the component that you are testing so you imported the component and then you pass
2:28:19
this one one so this is how you need to basically render a component for testing using react testing library now let's
2:28:26
move on to the next one how do you find elements in Dom using react testing
2:28:31
library now here the question this answer can be very vast right it is not
2:28:37
a single thing because there can be multiple things you can do but in interview you can give some simple
2:28:43
example that okay whenever I need to find any elements in a component right first I need to render the component
2:28:50
this is the first step so to render a component we render from react texting library and then what I'm checking that
2:28:56
okay I'm checking in my in this component I have a text or not let's say I have a Hello World
2:29:02
text and to do that we can basically use screen method from this react testing
2:29:08
Library which will give us all the matches so here this is one of that get by text something like that you have
2:29:14
gate by role like lot of things you can have gate by tag right so here we need
2:29:20
we are basically uh checking the element that if this text is present in this
2:29:25
component or not so we doing screen. get by text and this component and then we are checking that okay this element to
2:29:32
be in the do document means this element has to be in our browser or you know Dom
2:29:37
so this is what you can do so you first render the element check using a matcher
2:29:43
that whether this element is present or Not by what so you are expecting this element to be in the document so this
2:29:49
will be the simple example now let's move on to the next one how do you simulate user events or on click in your
2:29:55
react testing library and this is also like very not very tricky but simple
2:30:02
first you need to render the component again right and then first you checking the button first you're getting the
2:30:07
button so you have a button right click button let's say so first how you getting by roll G by roll so this is
2:30:14
what I mentioned so you have get by text get by roll so you're getting the button and then you're passing the increment so
2:30:19
so let's see you have a button here which says increment so first you're getting the
2:30:25
button and then you're importing another method that is called fire event so what is does that you're telling that fire
2:30:30
event. click on button means every time we click on this increment button this is what exactly this will do and then
2:30:37
what I will do that I'll checking whenever I'll click on this button the count one should be in the document so
2:30:43
first time it will be zero I fired this event here so I clicked one time this
2:30:48
will become one right again I clicked this will become two so that means that is what exactly I'm
2:30:53
checking that if I click on this button the count one should be in the document so this is how you need to explain in
2:30:59
interview that how you can handle user events in your react testing Library let's move on to the next one
2:31:06
how to test props in Thea testing library now to test a props again again
2:31:12
and again the first thing will be always to render the component so you render the component and you pass a dummy props
2:31:18
that we are passing a props which is title and what I'm checking that I'm expecting this title to be in the
2:31:24
document that if this title test title should be in our Dom as simple as that let's say you have another prop which is
2:31:30
a number and you're passing 100 so again we'll check expect this 100 to be in the
2:31:37
document so what will be the step so first you'll tell your interview that first I need to render this component
2:31:42
and then I'll pass a dummy prop here whatever props this component is expecting and then I need to check
2:31:47
whether this title is present in the document or not as simple as that now let's move on to the next one now from
2:31:55
this part I created some questions where you will get some handson uh interview questions also right handson right so
2:32:02
first thing like uh your interviewer can tell you like okay create a control input element now this is not Theory
2:32:08
questions these all are uh handson so what I'll suggest please try to implement all of this by your own again
2:32:14
we learn right how you can create a control component so control component means which state will be managed by
2:32:20
component state so we have input we have a button we take a state we manage the
2:32:25
handle on change and then we are doing a handle click that we are entering the current value now I'm not going to
2:32:31
explain all of this in details because the reason I created this question so that it will give you some handson experience also so this is one of the
2:32:38
question create a control input element so try to create this let's move on to the next one another question Implement
2:32:44
toggle visibility of a component means you have a button and you have you have a component
2:32:51
first time you'll click on this button you need to S this again you'll click on this button you need to hide this this
2:32:57
is what exactly this will does so how we can do that so we have a pattern component we have a button and on click
2:33:04
of this what we are doing we are basically toggling this said visible from True to false false to true and
2:33:10
then simply we're doing if visible if this is true then only I will render this child component or not try to
2:33:16
please try to implement by your own right now let's move on to the next one again very very important I'm not going
2:33:23
to explain this also because this is extremely important question please try to implement fet data from API and
2:33:29
display display it with loading State I think we have learned lot of time uh times how you can do that so you can see
2:33:36
that I already given this placeholder that Implement loading state so try to implement by your own this question I'm
2:33:42
pretty sure if you're giving some intermediate level of interview you will get this question like they will give
2:33:47
you API URL and then you need to implement this logic now let's move on to the next one all right this is a very
2:33:54
interesting thing create a reusable button component with props so what you need to do right let's say uh you are
2:34:02
creating very large application where you're are having 100 buttons you need to use instead of creating the buttons
2:34:07
multiple times you create a functional component which will receive the props from parent component so that you'll be
2:34:14
able to reuse reuse this component from 100 pages so what we have done right we created a button this will text uh
2:34:20
receive a text and on click and we're passing this here and then wherever it
2:34:26
is required from that component I'm just importing this component now I'm explaining in very simple way the reason
2:34:32
is because I want you to implement all of this by your own right place yourself
2:34:38
in such a place that okay think that I'm giving a real interview and then ask the question as
2:34:44
intervie Implement a reusable button component with props and then again
2:34:49
think yourself as a candidate and try to write it I hope you're getting what I'm trying to say okay and believe me this
2:34:55
way it is very very it you'll be able to replicate your interview environment in your home only so that it will be easy
2:35:02
for you in your interview to implement all of this now next we have another one that build a component that uses a use
2:35:09
effect which will perform a cleanup so I'll give you one example so I created a timer component where I have a second
2:35:16
state and every second I am basically ining using a set interval right and
2:35:22
increasing the count by 1 to 2 2 to three and then every time I'm cleaning
2:35:27
cleaning up this interval here in the return because use effect will return a call back right so this is what I want
2:35:34
so try to implement a timer component by your own and also do something like this you keep a button whenever you click on
2:35:40
this button you need to pause this timer and again if you click it you need to resume it something like that so try to
2:35:46
implement this also next Implement a context with a reducer for Global State
2:35:52
Management very very important so use context plus use reducer right so what
2:35:58
you need to do right till now we have learned this counter example multiple times so try to implement this counter
2:36:04
example using context and using use reducer right try to do that and let's
2:36:11
see go to the next one all right this is also another very important one that build a component with conditional
2:36:17
rendering based on props right so what we are doing right here you can have
2:36:22
multiple condition let's say you are having a condition one for condition one you need to render component one for
2:36:29
condition two you need to render component two for condition three you need to render component three and you
2:36:35
can have 10 condition so how you're going to do that so this condition let's
2:36:41
say you're receiving from props so this is your condition and you need to take a switch case so for condition let's say
2:36:47
this is your condition one you need to render component one if this is condition two you need to render
2:36:53
component two if this is condition three you need to render component three I hope you're getting this question is
2:36:58
also asking comp uh companies like atlassian like uh try to implement a
2:37:03
component which will be based on switch uh statement so you'll be receiving a props from your parent component you
2:37:09
will be having a switch statement and based on the condition you need to render different different component so
2:37:15
try to implement this and then we are having at the end Implement a simple form component so this is also very very
2:37:23
important that create a simple form there will be a button on click of this you need to submit that form and also
2:37:29
try to implement the handling error functionality also and this will be also very very important so I think these all
2:37:37
the 100 questions that we covered in this particular video I'm pretty sure that if you already have idea on react
2:37:42
Redux those things this video is going to help you immensely I'm pretty sure if you don't have I highly suggest please
2:37:49
learn react Redux first then you can use this video for your revision purposes so that's all for this particular video If
2:37:55
you like this video give a like comment down and please subscribe to my channel I'll see you in my next video till then
2:38:00
good luck and peace