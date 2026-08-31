# Spring boot AOP (Aspect Oriented Programming)
> YouTube transcript — video ID: HhsAw8GVogQ

## Chunk 1

[00:01] hey guys welcome to concept and coding
[00:02] this is Shan and today in Spring boot we
[00:05] are going to complete this spring aop so
[00:09] I'm taking it Mark let's start with
[00:13] aspect oriented programming which is aop
[00:16] and that is being used by many other
[00:20] topics which we are going to cover like
[00:22] transactional okay that's why I wanted
[00:24] to cover it before so in simple term
[00:30] if you want to explain aop we can say
[00:32] that it helps to intercept the method
[00:36] invocation right and we can perform some
[00:40] tasks before and after the
[00:42] method okay so what aop says that hey
[00:46] you allow it allow us to focus on
[00:49] business logic by handling boilerplate
[00:52] and repetitive code like logging
[00:54] transaction management Etc what I mean
[00:56] to say here is let's say you want to
[00:59] have certain business logic like this is
[01:02] your current business logic but many

## Chunk 2

[01:05] times there are certain piece of code
[01:08] which we have to write let's say you
[01:09] have to keep logging certain things you
[01:13] have to keep logging after your business
[01:15] logic runs and also transaction you have
[01:18] to start transaction you have to end the
[01:21] transaction and if some uh issue comes
[01:24] you have to roll back okay so there are
[01:28] few things which is apart from from your
[01:30] business logic that is known as
[01:32] boilerplate means which you have to do
[01:35] and these are repetitive means it is not
[01:37] just for one one class or one method if
[01:41] you have 100 methods which required
[01:43] logging you have to do the same thing if
[01:45] you have 100 method which requir
[01:46] transactional property you have to start
[01:48] and end the transaction roll back all
[01:50] these things so these are repetitive
[01:52] code in your
[01:54] business uh repo so that's where aop
[01:57] says that hey you focus on business

## Chunk 3

[01:59] business logic this boiler plate and
[02:02] repetitive code I will take care of it
[02:04] so you don't need to handle put it over
[02:07] here you can remove logging and
[02:09] transaction roll back all you have is
[02:11] now your business logic and somehow this
[02:14] logging transaction management aop will
[02:17] take care of it how we will see
[02:22] that so aspect so when we says that
[02:25] aspect oriented programming what is
[02:28] aspect means as p is a module which
[02:32] handles this repetitive and Boiler code
[02:34] so I told you right this repetitive and
[02:37] Boiler code like logging and all
[02:40] transaction uh commands and all these
[02:42] are repetitive and Boiler code so all
[02:45] this logic can go to a particular place
[02:48] that we call generally an
[02:50] aspect so what does it helps it helps in
[02:53] achieving the reusability and
[02:55] maintainability of the code definitely
[02:57] so now in this aspect let's say we have
[03:01] put

## Chunk 4

[03:01] logging now if even at 100 places you
[03:05] want to put uh the log right you don't
[03:09] have to write the same logic again and
[03:11] again at 100 places uh in your main Core
[03:14] Business Place you don't even have to
[03:16] write it aop will automatically take
[03:20] care of putting the logging either you
[03:21] want before or after or both right so
[03:25] all the 100 places can use this
[03:28] code right so if it helps in achieving
[03:31] the reusability and the maintainability
[03:33] of the code so only one place is where
[03:36] it has to maintain and any changes made
[03:39] it here all 100 places will get impacted
[03:43] with that so maintainability is
[03:47] easy so dependency so before we start
[03:52] using aop this dep uh this dependency we
[03:56] have to add into our pal. XML so you can
[04:00] add this dependency in your form okay
[04:05] spring hyphen boot hyphen starter hyphen
[04:08] aop okay this is very very simple

## Chunk 5

[04:11] example when I'm showing you the demo
[04:14] like what exactly it does but don't
[04:16] worry about this uh whatever you see
[04:19] here right at the rate expect at the r
[04:22] before don't worry about it at all it
[04:24] just want to show you that when I told
[04:27] you it helps to intercept the method
[04:28] what exactly it is so now let's say that
[04:32] this is one of my class now in this
[04:34] class this is a rest controller class
[04:36] where I have exposed an uh rest API like
[04:39] path this fetch employ /
[04:43] API slash fetch employe I have exposed
[04:47] like
[04:48] this now here if you see that I am just
[04:51] returning item fetch so this is my
[04:53] business logic this is my business logic
[04:57] but I wanted
[05:00] something
[05:02] before it return before this method get
[05:06] executed I have to perform certain task
[05:09] so what happen is I have here if you see
[05:12] you won't see
[05:13] anything but this is one aspect I

## Chunk 6

[05:17] created in that I have written one
[05:22] method don't worry about all these
[05:24] things how this I have written one
[05:25] method which does something let's say
[05:28] logging consider this is it is is
[05:30] logging consider this system. print
[05:33] Talent is at I am
[05:35] logging so I am just logging that hey I
[05:38] am inside this before method
[05:40] aspect okay now I started the
[05:44] application so here if you see
[05:46] application started
[05:48] properly now I am hitting the request
[05:51] that in the Local Host I am hitting this
[05:54] API fetch employ
[05:58] now before the invocation of this before
[06:02] the execution of this method what would
[06:05] happen is this before method will get
[06:08] invoke so this will logging will happen
[06:10] inside before method aspect so here if
[06:13] you see it will first print inside
[06:16] before method
[06:18] aspect after this it will return the
[06:21] item fetch it after this it will return

## Chunk 7

[06:24] the item
[06:25] fetch okay so this is what I mean to say
[06:28] when I say that aop helps you to
[06:30] intercept the method right so before
[06:34] this method get invoked it intercepted
[06:36] it it performs certain
[06:39] task right and then it calls the method
[06:43] then this method Works happen and if
[06:46] there is something after you have to
[06:48] do so there is uh you can also perform
[06:52] certain task after this method execution
[06:55] also now the main thing what exactly how
[07:00] it is happened how this interception
[07:03] happen how this interception internally
[07:06] works right so now we all have to
[07:09] understand that
[07:11] part now let's slowly goes to each and
[07:15] every part of it
[07:18] okay if you don't understand in a single
[07:20] shot please check it again I will try to
[07:23] go slow because this is lot of things
[07:26] going to come into
[07:28] this okay okay so first thing
[07:32] first the aspect class where we are

## Chunk 8

[07:35] going to write our Boiler code
[07:38] right we have to annotate that class
[07:41] with ad theate
[07:43] aspect okay this aspect has certain
[07:46] purpose so spring boot get to know that
[07:49] okay this logging aspect because this is
[07:52] at theate component when you start an
[07:55] application right spring boot scans so
[07:57] when spring boot find this
[07:59] hey this is this class is annotated with
[08:02] at the rate aspect then spring boot
[08:04] knows that okay what does it contain it
[08:06] it contains certain
[08:09] methods which might require
[08:12] interception right which might need to
[08:14] be get executed before certain method or
[08:16] after certain
[08:18] method so now here if you see that the
[08:21] first part is your point
[08:25] cut so this annotation here if you see
[08:29] this before this method I have put this
[08:33] at theate before and there is certain
[08:37] expression so this expression this

## Chunk 9

[08:42] expression this expression is known as
[08:46] point cut what what point cut is it's an
[08:50] expression which tell where an advice
[08:52] should be applied advice is what advice
[08:55] is this method actually
[08:59] this method plus
[09:02] this before or
[09:05] after Okay so this point cut what happen
[09:08] is it matches it do some matching logic
[09:11] that okay this class this class and
[09:15] inside this class this
[09:17] method okay some matching happened okay
[09:20] for this method I have to do some
[09:22] interception means before this method
[09:25] actually get invoked I have to run this
[09:29] whether before or after this will tell
[09:31] whether before I have to run or after I
[09:33] have to run okay but how to find out
[09:37] which method we have to run this code
[09:41] whether before or
[09:43] after it is tell by point cut how to
[09:47] identify that particular class or
[09:49] particular method where we have to run

## Chunk 10

[09:51] this piece of code is tell by point
[09:55] cut so now let's go through this
[09:58] expression
[10:00] one by one there okay so now we are
[10:03] going to this point cut we are going
[10:05] deep into this point cut now so point
[10:08] cut definition now you already know it's
[10:10] an expression which tell where an advice
[10:12] should be applied
[10:14] okay this is what actually is an advice
[10:18] what actually the code has to run before
[10:20] the method and after the method but this
[10:23] is what point cut actually
[10:26] tells which for which method this has
[10:29] has to be done so type of Point C so
[10:34] first is
[10:36] execution so here if you see that in the
[10:39] execution what it says that matches a
[10:42] particular method in a particular class
[10:46] it matches a particular method in a
[10:48] particular class so with this execution
[10:51] here if you see that we have to give
[10:54] expression like this so this expression

## Chunk 11

[10:56] has certain part the first part is is
[11:01] your access
[11:04] modifier whether it's public private
[11:07] protected what right and this is
[11:11] optional this is
[11:14] optional means even if you remove it
[11:16] doesn't
[11:18] matter it will check for all it will
[11:21] check for private public protected all
[11:24] okay so this is
[11:26] optional and this is your exis
[11:32] modifier the second part this is your
[11:35] return type method return
[11:39] type okay so whatever the return type of
[11:41] your method you will write here and this
[11:44] is not like an optional you can skip it
[11:46] you have to provide it
[11:49] okay and the third part is
[11:53] your the path for your method so this is
[11:57] your package com do concept and coding
[11:59] do learning springbot right this is your
[12:02] package this is a class name and inside
[12:05] this class name this is a
[12:07] method so the full method the class path
[12:11] has been

## Chunk 12

[12:12] given com. concept coding. learning
[12:15] springboard do employ do method name
[12:18] fetch
[12:19] employe okay and this method doesn't
[12:22] have any parameters so that's why it is
[12:23] empty otherwise inside this we can
[12:26] provide the parameters whether it takes
[12:27] a string in some object object and all
[12:30] so but here in our
[12:34] example in this case if you see this
[12:37] fetch
[12:38] employee this has no arguments so that's
[12:42] why I have kept it empty
[12:46] also okay so
[12:50] here so this one you got it right
[12:53] execution what execution it it's always
[12:55] focus on whenever you are using this
[12:57] type of point cut execution
[12:59] it always focus on try to match a
[13:03] particular method in a particular class
[13:07] right and you have to give this
[13:11] way okay now there are a wild card which
[13:16] we can use so there are two type of wild
[13:18] card whether using star or dot

## Chunk 13

[13:23] dot okay so let's see that if we want to
[13:26] use a wild card how we can do it so
[13:29] let's say that we want to use a star so
[13:31] star means it matches any single item
[13:35] now let's so now let's say this is the
[13:37] class now I want to use this wild card
[13:40] how to use any wild card like matches
[13:42] any single item now let's say I'm
[13:44] writing an execution means this type of
[13:46] point cut means I have to point to a
[13:49] specific method where this method has to
[13:53] be run right so matching this is the
[13:56] matching logic so first I use star so
[14:00] now here if you see that I have removed
[14:04] this because this is optional this is
[14:07] not even required if you don't write it
[14:11] it will check for public private
[14:13] protected all type of exess modifier so
[14:15] I started with this return type so
[14:18] return type instead of string now I give
[14:21] estess so no
[14:23] matter a string or int or any object

## Chunk 14

[14:28] doesn't matter
[14:29] so this is one wild card now I provide
[14:33] the total class for for my method
[14:37] employ then this method name that before
[14:42] uh uh for this method I have to do some
[14:47] interception and this doesn't accept any
[14:50] argument so I have kept it
[14:53] empty okay so this what would happen is
[14:56] so now spring boot will match this point
[14:59] cut expression with this
[15:01] method right and it able to identify
[15:04] that okay for this method I have
[15:09] to run this advice run this method now
[15:14] whether before or after we will come to
[15:17] that later but at least now it filter
[15:19] out that okay this
[15:22] is this method
[15:25] is matched with this point cut
[15:30] okay now the second matches any method
[15:34] with single parameter string so now here
[15:36] if you see that I am trying to do an
[15:39] execution means again one direct
[15:42] particular method it have we have to

## Chunk 15

[15:43] point out star it started with the star
[15:47] space so means this is the return type
[15:49] whatever the return type could be a
[15:50] string integer doesn't matter com do
[15:54] concept and coding do learning is spring
[15:55] boot. employer so this is still I have
[15:58] provided a particular class now what is
[16:00] the method do star now doesn't matter
[16:05] whether fetch employee or you can say
[16:08] that
[16:09] in uh some update
[16:14] employee update
[16:16] employee so this star means any method
[16:21] any method name now I haven't provided
[16:24] any specific method name I provided star
[16:26] means any method name return type also
[16:28] Al I have used a star so doesn't matter
[16:30] whether it's string or int So currently
[16:32] till now matching is happening now in
[16:35] the parameter I have given a string so
[16:38] means method should have taken an string
[16:42] so let's say one argument is a string

## Chunk 16

[16:45] well so now the matching will not happen
[16:48] for this because okay return time
[16:51] matching because this is a star wild
[16:53] card so this is okay fetch method okay
[16:57] because this is method is star any
[16:59] method name could be there but matching
[17:02] is like the method should have argument
[17:04] one one argument should be string does
[17:06] it have any argument no this method has
[17:09] any argument yes so this got matched
[17:13] with this this point could get matched
[17:15] to this
[17:16] method so now whenever somebody try to
[17:19] invoke this
[17:21] method this will run either before or
[17:25] after we will see
[17:27] later one more example of execution
[17:29] which I want to give so I'm running an
[17:33] execution now a string specifically now
[17:35] I'm giving that return type should be
[17:39] string this should be the method
[17:41] specific I have provided the exact part
[17:45] to this method and also return type I

## Chunk 17

[17:48] have given is
[17:49] star star means single should get match
[17:53] right I told you star me match any
[17:55] single item so even though there so this
[17:59] doesn't take any method any argument
[18:02] this fetch employer doesn't take any
[18:04] argument so it will not match because it
[18:07] is expecting one argument either a
[18:09] string either in either object doesn't
[18:11] matter but when we have put a star means
[18:14] at least one should be there so this
[18:16] matching will not
[18:18] happen Okay so now you okay so now you
[18:23] understand this uh star Wild Card Asis
[18:26] wild card now I'll tell you about the
[18:29] second Wild Card dot dot so it matches
[18:32] zero or more item mean zero or
[18:36] more so first example which I am giving
[18:39] you what is this it matches the fetch
[18:42] employe method that take zero or more
[18:44] parameter so read this execution means I
[18:48] have to provide one specific method

## Chunk 18

[18:51] matching return type is a string this is
[18:54] the class path exactly for the
[18:56] particular method so this is my package
[18:59] this is my class and this is my method
[19:01] name okay so till now I have provided
[19:04] fully now here if you see that in the
[19:06] arguments I have put dot dot
[19:10] means either this fetch employe have
[19:13] zero argument or more than like more
[19:17] than zero like or more item it will get
[19:19] matched so now in this case this got
[19:23] match with
[19:24] that right so let me copy it here so
[19:27] that it would be easy
[19:30] easy so now here if you see that even
[19:33] the fetch employee has zero arguments it
[19:36] will get match because dot dot means
[19:39] zero or
[19:41] more now see the second example of uh
[19:44] this one I am running an execution means
[19:47] a specific class method I have to
[19:50] provide
[19:52] execution a string this is a return
[19:55] type com do concept and coding do dot

## Chunk 19

[19:59] now here dot dot means any package any
[20:04] subpackage right and ultimately this is
[20:08] the method name I have provided so now
[20:11] com do concept and coding dot like
[20:14] whatever the package subpackage would be
[20:17] in any package sub package and whatever
[20:19] the classes it has if any method name is
[20:23] fetch
[20:24] employee within this concept and coding
[20:27] package and it's package if any method
[20:30] has fetch employee matching should have
[20:32] happened with
[20:34] that
[20:38] okay now there is one more thing I want
[20:40] to show that execution a string this is
[20:43] a return type com do concept and coding
[20:47] dot dot means concept and
[20:53] coding and this package and inside this
[20:57] any other package is required so it will
[20:59] look for all uh this package and all
[21:02] other sub
[21:03] packages right all the classes inside
[21:06] that all the classes inside this sub
[21:08] packages also and which method I have

## Chunk 20

[21:10] put a
[21:11] star like doesn't matter uh so all the
[21:17] methods inside the package and sub
[21:20] packages of
[21:22] this this match point cut should get
[21:26] match
[21:29] okay so
[21:32] execution execution now you know this
[21:36] now let's say second type of point cut
[21:37] is
[21:39] within now within so what within says
[21:42] that matches all method within any class
[21:46] or
[21:48] package how now let's say I want to run
[21:51] all the methods for within a class we
[21:55] can do it through execution also I told
[21:57] you right through execution also we can
[22:00] run this way but there is a simpler way
[22:03] with the within also so here here if you
[22:06] see within so this is another type of
[22:08] Point cod in this within there is
[22:10] nothing like a return type because we
[22:12] are not specifically pointing to a
[22:14] method now we are giving here either the
[22:16] class path or the package path com do

## Chunk 21

[22:20] concept and coding. learning springbot
[22:22] do employe so I have provided a
[22:25] particular class so all the methods with
[22:28] within a within this
[22:31] class this point cut will get
[22:34] match right if this
[22:38] employee if this employee class
[22:42] has four
[22:45] methods right so this point cut will
[22:47] match for all
[22:49] four okay so no matter if you are
[22:52] calling this method then also this
[22:56] matching will happen and whatever the
[22:58] advice we have to
[23:00] run like below this whatever the method
[23:02] we will write it will get
[23:06] run now if you want to run on a package
[23:09] we can say that within com. concept and
[23:13] coding learning is spring boot dot dot
[23:16] right and estess no matter any
[23:21] class now learning a springbot package
[23:25] or below sub
[23:27] packages any class which is present
[23:29] inside this package and sub packages for
[23:33] that this point cut will get
[23:36] match within point

## Chunk 22

[23:39] cut there is one point cut called at the
[23:42] rate within so whenever we use at the
[23:46] rate right so at the rate within
[23:49] means here we have to provide an
[23:52] annotation we don't have to provide a
[23:55] class path of a particular class we have
[23:58] to provide Prov an
[23:59] annotation okay matches any method in a
[24:05] class right which has this annotation So
[24:09] within you already know that within
[24:11] works on a class level right so when we
[24:15] use atate within
[24:17] means any class which this annotation
[24:22] which has this
[24:23] annotation this point cut will
[24:26] match okay so here is if you see this
[24:28] example I have written one simple class
[24:32] rest
[24:33] controller where this is one method
[24:36] which has exposed this API / fetch
[24:39] employee now this fetch employee is just
[24:42] calling one utility class employee util
[24:45] I have autoed it employee helper method

## Chunk 23

[24:48] certain helper method now this employee
[24:51] util class I have put at theate
[24:55] service okay and this is one method
[24:58] employee helper
[25:03] method so this will print this and after
[25:05] that it will return item fetch so very
[25:08] very simple this two classes are very
[25:10] very simple it's just my business logic
[25:12] I have used now I have put this aspect
[25:17] class where I want to do something
[25:21] before a particular method invoke so I
[25:25] have put add
[25:27] within okay within means targeting to a
[25:30] specific class but at the rate is like I
[25:33] have to provide The annotation
[25:36] here I have put this
[25:39] service annotation path okay so now what
[25:43] is springboard will know that okay any
[25:48] class which has this
[25:52] annotation right all its method this
[25:55] match will
[25:56] happen I have
[26:00] invoked this API fetch
[26:02] employee now when this API is invoked
[26:06] what would happen

## Chunk 24

[26:08] is currently any aspect match currently
[26:12] any any point cut match with this no So
[26:16] currently atate within is any class
[26:18] which has service annotation this class
[26:20] employee has service annotation no so
[26:23] there is no matching happen now it
[26:26] proceed and it calls employ U employ
[26:29] helper method now it is trying to invoke
[26:32] this now springb say that okay this
[26:35] method before I invoke this method is
[26:38] there anything I have to do now it will
[26:41] see that okay there is some aspect
[26:44] present at theate within the class any
[26:48] class which has this annotation at
[26:50] theate service okay this class has this
[26:54] annotation okay means this got match up
[26:59] this point cut will get match up
[27:02] means this method has to be run before
[27:06] or after So currently we are telling
[27:09] before so before this method execution
[27:12] this will run inside before method

## Chunk 25

[27:14] aspect so it will print inside before
[27:17] method aspect and after that it will go
[27:20] inside this and it print employe helper
[27:23] method call employee helper method call
[27:26] and after that it will put item fetch to
[27:29] the
[27:33] UI okay you got atate within So within
[27:36] this deal with the classes all the
[27:39] methods within a
[27:41] classes but when we have put add theate
[27:43] means it has we have to give annotation
[27:47] all classes which has this
[27:51] annotations okay now another type of
[27:55] point cut is ADD theate annotation now
[27:57] this deals with the meth method matches
[28:00] any method that is annotated with given
[28:04] annotation okay so here see this one I
[28:09] have written one aspect class put at
[28:11] theate
[28:12] aspect right this is also have to use at
[28:15] the at theate component because this has
[28:17] to be otherwise spring board will not
[28:19] manage it so we have to use at theate

## Chunk 26

[28:21] component also because this is also a
[28:22] bean object this
[28:24] required so I am using the point type is
[28:28] at theate annotation what does at theate
[28:30] annotation is so we are using at theate
[28:34] means right we have to provide some
[28:36] annotation path so what annotation path
[28:38] I have given get mapping this annotation
[28:42] path I have
[28:43] provided okay so what ad theate
[28:45] annotation is that matches any method
[28:49] that is annotated with given
[28:51] annotation okay so now what would happen
[28:53] is I invoke this method when I invoke
[28:57] this method fetch employee is springbot
[28:59] before running this method it sees that
[29:03] hey any aspect is which is getting match
[29:06] any point cut which is matching it will
[29:09] see that okay at theate annotation is
[29:12] there which says that any method which
[29:14] has G mapping annotation yes it has G
[29:17] mapping annotation this method has G

## Chunk 27

[29:19] mapping annotation means this has to be
[29:22] run before or after currently I'm
[29:25] telling it at theate before if I want to
[29:28] run I can tell at the rate after if I
[29:30] want to run after this method So
[29:33] currently I'm telling is at theate
[29:34] before so means it will run first inside
[29:36] before method aspect and then it will go
[29:39] inside this and return this item
[29:42] fetch so you got it at theate
[29:49] annotation then there is something
[29:50] called
[29:52] ARS matches any
[29:55] method with particular argument
[29:59] so now here if you see this is another
[30:01] point cut type where this is like a AR
[30:03] GS ask and inside this like you want to
[30:08] give like any method which takes this
[30:10] type of argument a string comma int so
[30:13] first is a string second is in so here
[30:16] if you see
[30:18] this
[30:20] asks a string comma int I have given as
[30:23] a point cut
[30:26] expression okay so at the aspect is

## Chunk 28

[30:28] there in this class component and this
[30:31] is the method like any method which got
[30:34] match with this this method has to be
[30:36] done before its
[30:39] execution so now what I am doing
[30:42] is here I am calling this
[30:45] API now when I'm calling this API so
[30:49] here if you
[30:50] see currently
[30:52] this this got matched no it has argument
[30:57] string comma and does it taking any
[30:59] argument no so no matching happen so it
[31:01] will go inside it will run this the
[31:05] statement employe util employ helper
[31:08] method and it passing two parameters so
[31:11] it is trying to invoke this
[31:14] method so this method when a spring
[31:16] board try to execute this method it will
[31:18] check hey any point cut matches happen
[31:22] so it will say that okay there is a
[31:24] point cut which says that argument which
[31:26] takes a string comma and any method
[31:28] which takes the string
[31:30] command
[31:31] yes this

## Chunk 29

[31:33] is applicable for this it got matched
[31:36] with this point cut means this has to be
[31:39] done and before so this will print first
[31:42] inside before method
[31:45] aspect then it will go inside this
[31:47] employer helper method call and after
[31:50] that it will return
[31:52] this got it ask
[32:00] right okay so now one question can comes
[32:03] to that okay hey what if instead of uh
[32:06] string in if we have object how we give
[32:10] so we can give like ask and give the
[32:12] proper class path of that class till
[32:14] class level like
[32:17] any object of this class com. concept
[32:20] and coding do learning springboard do
[32:23] employ right so it will match to any
[32:26] method that accept a reference for this
[32:33] class and there is something called at
[32:35] theate ARS now whenever at theate comes
[32:38] before this at theate means we have to
[32:41] provide the path for The
[32:43] annotation okay so how to read this is
[32:48] matches any

## Chunk 30

[32:50] method with particular parameter and
[32:53] that parameter class is annotated with
[32:56] particular annotation now here when I
[32:59] give atate ask and this is The
[33:01] annotation service so what I'm looking
[33:04] for is here if you see atate ask and I
[33:07] have given the path for service
[33:09] annotation so what happen is it will
[33:12] look for any
[33:15] method any
[33:19] method that accept one that accept
[33:24] any argument
[33:28] okay and that argument class
[33:30] right has this annotation service
[33:34] because see ask is deal with the
[33:36] argument we don't have to worry about
[33:38] the method name and all any method but
[33:41] the argument which you are passing does
[33:45] that argument has this that class has
[33:48] this annotation so here the argument is
[33:50] employ Dow let's say this and so this is
[33:54] one method which is ultimately getting
[33:55] invoked let's say and this me method has

## Chunk 31

[33:58] argument employed Dow now this employed
[34:00] Dow class had this annotation at theate
[34:03] service so this got matched up okay so
[34:07] AR deals with the argument and atate AR
[34:10] says that the argument which you are
[34:13] getting the Class Type does this has
[34:16] this annotation if yes then only do the
[34:19] matching with
[34:20] this so This method has employed Dow and
[34:23] this employed Dow has adate service
[34:26] which got matched this with anotation so
[34:28] this is a match for this point
[34:34] cut okay this is the seventh type of
[34:37] point cut which we can use matches any
[34:40] method on a particular instance of a
[34:43] class okay so here at theate aspect so
[34:47] this is the class where we are writing
[34:48] all the point Cuts so here I'm using
[34:50] Target so Target is your one type of
[34:53] point cut expression uh point cut type
[34:56] so Target now here what we have to give
[35:00] we have to give a till class level path

## Chunk 32

[35:04] so this is my
[35:06] class now whenever an instance of this
[35:10] class is used to call any
[35:14] method this will get
[35:16] matched so just see this example in this
[35:19] class very very simple class employee
[35:22] rest controller expose this
[35:25] API does this mapping
[35:28] now I'm calling this
[35:30] method
[35:32] okay fetch employee it is running this
[35:34] employ util do employ helper method so
[35:39] now it will see that hey any point cut
[35:43] match happen so here Target means says
[35:45] that in the Target what is the class I
[35:48] have given employee
[35:50] util whenever this instance of this
[35:53] class so this is an instance of this
[35:57] class
[35:59] is used to invoke a particular method
[36:01] for that method this got matched
[36:05] up so is it
[36:07] clear and there is one more uh the
[36:10] target flavor of this is like we can
[36:12] even provide an interface also instead
[36:14] of direct class instead of direct class

## Chunk 33

[36:17] we can provide an interface so now here
[36:19] if you see that this is the class
[36:21] structure I have
[36:22] created okay the controller class this
[36:25] controller class has
[36:28] dependent
[36:30] on employee interface so I have created
[36:33] one employee interface this employee
[36:35] interface has two
[36:37] child temp employee Perma employee
[36:40] permanent employee so this has two type
[36:42] of employees okay so you know already
[36:45] that we have to use qualifiers properly
[36:48] because if we have to use we have to
[36:49] tell which dependency we it has to
[36:54] be put inside this employee object
[36:58] object okay and I am using that employee
[37:00] object by calling the method if you see
[37:03] this
[37:04] aspect I writing a point cut for the
[37:07] type Target and what I have
[37:12] given till interface level I have given
[37:15] this interface name so what this
[37:17] interface name is
[37:19] that any child classes for this

## Chunk 34

[37:24] interface like if it is an instance of
[37:26] Temple employee
[37:28] or if it is an instance of permanent
[37:31] employee doesn't matter because this is
[37:33] an interface I have given right so no
[37:35] matter whatever the child instance it
[37:38] has this is applicable so now here if
[37:40] you see that I am calling fetch employee
[37:43] method employee on a temporary employee
[37:46] object because I have put a qualifier
[37:48] temp employee so it's I'm creating an
[37:50] object of this so even though you are
[37:52] creating an object of this temporary
[37:54] employee this this point cut will get
[37:56] matched because this is an interface so
[38:00] for all its child instances also this is
[38:03] valid so it will run this before calling
[38:07] this method so I'm call use at theate
[38:10] before so means it will run first this
[38:11] inside before
[38:13] method and then it will go inside fetch
[38:16] employe method of a

## Chunk 35

[38:18] temporary okay so only point to say that
[38:21] when even if you use interface instead
[38:23] of direct class now with interface no
[38:27] matter how many child classes are there
[38:28] of this
[38:30] interface for that instance of those uh
[38:32] child classes this will get true this
[38:35] will get
[38:40] match okay now we can also one more
[38:44] thing is we can also combine two point
[38:46] cut so we have seen multiple point cut
[38:49] right which
[38:50] one
[38:53] execution
[38:55] within at theate Within
[38:59] asks at the rate
[39:01] ARS Target and at the rate
[39:05] annotation right so we have seen
[39:07] multiple annotation multiple Point Cuts
[39:10] we can combine them also we can use
[39:12] together also using and and or Boolean
[39:15] and Boolean or so here if you see that
[39:18] this is one example which I am
[39:21] giving I am writing one aspect class put
[39:24] at the
[39:25] aspect okay this is the method but this
[39:28] is my point cut

## Chunk 36

[39:30] expression so first is execution
[39:32] execution means pointing to a particular
[39:35] method return type is anything this is
[39:39] the
[39:40] package right so this is my
[39:43] class dot any
[39:48] method in this class any method any
[39:52] return type and it do not accept any
[39:56] argument okay
[39:57] but now here if you see that I have
[40:00] combined it with another point
[40:02] cut now I'm adding and and means it's an
[40:06] and both should get true then only this
[40:09] will get match up and this will should
[40:11] run at theate
[40:14] within within is deal with till class
[40:16] level so I have provided uh but I have
[40:18] used at theate so means annotation path
[40:21] I have to given so annotation path I
[40:23] have given is rest controller so any
[40:25] class which has this rest FR controller
[40:28] annotation okay so this is one and this
[40:31] is like similarly I have written for
[40:33] R now let's see that if I call this

## Chunk 37

[40:37] method if I call this what would happen
[40:41] so now this uh you have invoke this now
[40:45] spring boot will say that hey this
[40:46] method got this method got match with
[40:50] any aspect so first execution let's see
[40:52] this
[40:53] first any return type okay good com.
[40:58] concept and coding. learning springboard
[41:00] employ controller yes this is within
[41:02] this package and the class
[41:04] name any method name okay and uh this
[41:08] method doesn't accept any argument yes
[41:10] this got match so this is true this got
[41:12] matched now
[41:16] and any class which should have this
[41:19] rest controller yes this class has rest
[41:22] controller so this both get true means
[41:25] this is got matched with for this method
[41:28] and this should run and this should run
[41:31] either before or after I have put at the
[41:33] before so it will run inside before end
[41:36] method aspect inside before end method

## Chunk 38

[41:40] except okay so this is run and there is
[41:44] another so it will see try to match it
[41:46] with this
[41:47] also
[41:49] star so this got match up exactly same
[41:52] so this is
[41:53] true
[41:55] or we should have at theate component
[41:58] within means this class has at theate
[42:00] component no this doesn't have at theate
[42:02] component uh so this will get false but
[42:06] since this is or anyone should get true
[42:08] so this is also true so this is this
[42:12] method also has to be run but it before
[42:14] right so this will also get print inside
[42:16] before or
[42:18] method so now after this it will return
[42:22] item
[42:23] fetch there is one uh one more thing
[42:25] called named point cut so in the name
[42:28] Point part what we have seen this before
[42:30] is we have used add theate before and
[42:32] here we are used to give the point cut
[42:34] expression so we can name that
[42:37] expression so here this is the way of

## Chunk 39

[42:39] giving so I'm put using at theate Point
[42:43] Cod and give the
[42:45] expression so we are telling springboard
[42:47] that this is one point
[42:50] cut okay just provide a method name
[42:53] which should be empty we don't have to
[42:55] write anything inside it the purpose of
[42:58] this is that okay we are just giving the
[43:01] name of this point cut to this one this
[43:04] method name now this method
[43:07] name custom Point custom point cut name
[43:12] is now is the name for this
[43:15] expression okay so now instead of using
[43:19] this full expression again and again at
[43:22] multiple places let's say you can just
[43:25] use custom point cut name name like this
[43:28] so this is how I used it atate before
[43:31] now here if you see I have given custom
[43:33] point cut name this
[43:36] method now it will automatically use uh
[43:39] change it with this expression
[43:42] complete the bigger part is completed

## Chunk 40

[43:44] point cut now the advice I think while
[43:47] we were covering the point cut you
[43:48] already know this it's an action which
[43:51] is taken either before or after or
[43:54] around the method execution
[43:57] so we have seen this example right we
[43:59] have currently learning this uh point
[44:02] cut expression now the point cut we are
[44:04] done now the something is advice so this
[44:07] yellow part yellow part is known as
[44:09] advice so once this point cut got
[44:12] matched with any particular method after
[44:15] that this has to be run this is known as
[44:18] advice this advice has to be run either
[44:21] before after or
[44:23] around before is we have already seen
[44:26] after is self-explanatory that okay
[44:28] after that method invocation you have to
[44:31] run this advice but what is
[44:34] around around as the name says that it
[44:37] surrounds the method execution before
[44:40] and after
[44:42] both and it's very little very minor

## Chunk 41

[44:45] different from the before and after so
[44:48] now let's check
[44:50] this this is a point cut expression I
[44:54] have given I think now you can read this
[44:57] expression this is an execution which
[44:59] has to match with a particular method
[45:02] return type this is still class level
[45:04] path and any method okay so in the
[45:07] employee util any method any return type
[45:11] which doesn't take any argument this
[45:13] should get matched
[45:14] up okay so say that this employee util
[45:19] class any me uh any method because this
[45:22] is star any return type and which
[45:25] doesn't take any argument
[45:27] so this should get matched with this
[45:31] expression now once this is matched this
[45:35] advice has to be run before after or
[45:39] around I have tell around around means
[45:42] it is possible that we can run something
[45:44] before and after now see till now what
[45:49] we are using is at the before or at the

## Chunk 42

[45:52] rate after there what we have to do is
[45:54] we have to just write
[45:57] what we have
[46:00] to run before or after okay so now in
[46:04] the at theate before when we use at
[46:06] theate before what generally happen is
[46:09] it will simply execute this and
[46:12] internally internally it will call the
[46:16] method invoke the method if you are
[46:18] using at theate after it will internally
[46:22] first call the method and then execute
[46:25] this advice
[46:27] but in case of at theate
[46:30] around we have to call the method so in
[46:34] the
[46:36] around we have to use this joint Point
[46:41] proceeding joint point right so here in
[46:44] this case do whatever you have to do
[46:47] before the method use this joint point
[46:51] and call proceed method you have to call
[46:53] proceed method which will actually
[46:56] invoke
[46:58] your
[47:00] method and then you can do certain task
[47:03] after it so before then you invoke the

## Chunk 43

[47:07] actual method and do some after work so
[47:11] as the around says that it surrounds the
[47:13] method execution before and after if you
[47:16] need to perform any task you can do it
[47:17] then actually you have to invoke this
[47:20] method like this right it will take care
[47:22] of calling your method and if you have
[47:25] to do after task you can do this here so
[47:29] atate around is also very
[47:32] powerful advice which we can
[47:35] use now you can ask me right hey Shan
[47:39] how this adate proceed is actually
[47:41] calling the method I will tell you how
[47:43] internally it invokes also but first
[47:46] thing is that where we are is
[47:49] understanding what around
[47:51] us okay join point is nothing but the
[47:55] point where where we are actually
[47:58] invoking the method your actual method
[48:01] that generally in Spring spring boot aop
[48:05] we call joint Point joint point it
[48:07] generally considered a point where

## Chunk 44

[48:09] actual method invocation happen that's
[48:12] it so now we have seen lot of
[48:16] information now one thing might be
[48:18] bugging you as of today by now few
[48:21] question we all should have how this
[48:25] interception works I I understood what
[48:28] is point
[48:29] cut what is uh
[48:32] advice right different types of point
[48:35] cut I know different type of advice
[48:37] before after around I know I got it uh
[48:41] the matching happen with the point cut
[48:44] and uh if the matching happen before
[48:46] that actual method this advice will run
[48:49] so either before this advice will run
[48:51] and that method or after method this
[48:53] advice will run or around it but how
[48:57] this how this linking interception is
[49:01] working and what if you have thousands
[49:03] of point cut what if you have thousands
[49:05] of point cut so whenever I am
[49:07] particularly invoking a method I am
[49:10] particularly invoking a method so if I

## Chunk 45

[49:13] have thousands of point cut it is doing
[49:15] matching with all the point Cuts one by
[49:17] one by one will it
[49:20] not causing a problem in
[49:23] latency right so this question might be
[49:26] be bugging you very much how this become
[49:29] a so powerful tool if this is like too
[49:32] much
[49:34] complicated right so now let's
[49:36] understand how aop internally
[49:39] works I'll try to explain it in a very
[49:41] simple manner this is a very huge
[49:43] internally code based but I will explain
[49:46] you a very simple method which will help
[49:49] you to link
[49:51] everything okay so be with
[49:53] me so first when an application is
[49:56] startup
[49:57] happen okay I will also uh show you from
[50:01] the code also but first let's understand
[50:04] theoretically what is the step and then
[50:06] we'll show from the code when you start
[50:09] an application you know that spring boot
[50:11] looks for the beans so here in the first

## Chunk 46

[50:15] step it look for atate aspect annotation
[50:18] classes so this is the
[50:20] first now once the it found this classes
[50:24] now it knows that it this class contains
[50:26] point cut expression so the Second Step
[50:29] what does it do is it Parts the point
[50:31] cut expression parts means it simplifies
[50:35] those expression save it in a particular
[50:38] data structure so that it would be easy
[50:40] to do a matching it will do a parts of
[50:43] point cut
[50:45] expression and stored in an efficient
[50:47] data structure or Cache after
[50:51] parsing the third step is
[50:56] it look for atate component at theate
[50:59] service at theate controller ET
[51:01] annotation classes now at this point
[51:04] once it is started looking for at theate
[51:06] component at theate service all this
[51:07] type of another beings it checked if it
[51:10] is eligible for interception or not
[51:13] based on the point cut
[51:15] expression need not need not to be an

## Chunk 47

[51:18] exact method level but at least it knows
[51:20] that yes this class is valid for
[51:24] interception right so for each class it
[51:27] check it is eligible for interception or
[51:29] not based on the point cut
[51:31] expression and if yes it create a proxy
[51:35] out of it right if yes it create a proxy
[51:39] class either using jdk Dynamic proxy or
[51:43] cglib code generation Library
[51:47] proxy right so if you are writing this
[51:51] class employe
[51:54] util this is your class
[51:57] it has one method called let's
[52:00] say
[52:03] fetch does
[52:05] something right and during aspect and
[52:08] point cut it matches
[52:12] that and
[52:15] during point cut it fetches it it check
[52:20] that it is eligible for interception
[52:23] right if you have used uh dot dot asress
[52:27] now any class inside a package sub
[52:29] package so definitely this will come
[52:31] into the that
[52:34] uh interception right
[52:38] because any class inside this let's say

## Chunk 48

[52:41] concept and coding package and sub
[52:43] packages and this is inside that package
[52:46] only so definitely it comes into this
[52:48] radar so what it will do is it will
[52:50] create a proxy of
[52:52] it either using jdk Dynamic proxy or
[52:55] cgli proxy so now there is
[52:58] one employee
[53:00] util some at theate some 5 4 3 2 1 some
[53:04] random proxy class is
[53:06] made right and what it does it it will
[53:08] create a child class of it so now this
[53:11] become your parent and this will create
[53:13] one child
[53:15] class okay and it will overwrite this
[53:17] method atate public
[53:20] void
[53:23] Fetch and it will generate some so cglib
[53:26] and Dynamic is like it will generate
[53:27] some code now it will generate some code
[53:30] which will call certain spring framework
[53:33] so don't worry about this what what code
[53:35] is there but I'll tell you that
[53:38] understand this five step first first is

## Chunk 49

[53:41] look for ad theate aspect classes pass
[53:44] the point cut expression store it in an
[53:46] efficient manner Now look for all the
[53:49] other uh annotation
[53:51] classes now check if those classes are
[53:54] eligible for interception based on the
[53:56] point cut expression if yes then create
[53:59] a proxy of those classes using this
[54:02] to you might be say when to use jdk
[54:05] Dynamic proxy and when to use cgli so
[54:08] generally is
[54:09] like if your if your if your class is
[54:12] already a child of interface let's say
[54:16] employee
[54:19] util implement this interface let's say
[54:23] employee implements employee means there
[54:26] is this class is already a child of any
[54:30] interface then jdk Dynamic proxy is
[54:35] used okay if this class is not a child
[54:40] of any any interface then cgli is used
[54:44] because this cglib has the capability to
[54:47] create a
[54:48] subass of a particular class jdk Dynamic

## Chunk 50

[54:52] proxies just can create a new class and
[54:55] use just implement interface so it's
[54:57] automatically a child of this one but
[54:59] cgli is like when your class is not a
[55:02] child of any uh class then cglib is used
[55:06] it can create a
[55:11] subass okay now let's see
[55:15] that
[55:18] okay
[55:20] first I am starting the application I am
[55:24] starting the application now sh the code
[55:27] so here if you see that I have created
[55:29] one
[55:30] aspa some logging aspa and I have one
[55:34] before advice and after advice and this
[55:38] is the point cut expression which I have
[55:41] given right very very simple point cut
[55:44] expression I've given execution which uh
[55:47] matches with employee
[55:48] util class any method any return type
[55:53] right the same so in the before method I
[55:56] am just printing inside before method
[55:58] aspect and after method I am printing
[56:01] inside after method aspect so this is

## Chunk 51

[56:04] very simple aspect I have
[56:07] created now here if you see that I am
[56:09] starting the application
[56:11] now so now I starting the application
[56:14] now here if now here if you see the
[56:17] first control goes to where the first
[56:18] control goes to point cut parer so what
[56:21] this actually does is that it will Parts
[56:25] your expression
[56:27] okay so this is the first Parts the
[56:31] point cut expression it will goes to
[56:33] your point cut parser class and here if
[56:36] you
[56:37] see all your point cut expression it
[56:40] which resolve it into some simpler
[56:42] understandable and efficient data
[56:47] structure after
[56:50] passing the control goes to to wrap if
[56:53] necessary so here in this see now the
[56:57] second is this
[56:58] one the second control goes to in this
[57:02] class Auto proxy Creator wrap if
[57:05] necessary so here in this what happening
[57:10] is it will check it will now it is going

## Chunk 52

[57:13] through all the beans atate component at
[57:16] theate uh service at theate rest
[57:18] controller now it is checking hey does
[57:21] it required
[57:23] interception if yes then it is creating
[57:26] a proxy of it it is creating a proxy of
[57:30] it right if it if this class required if
[57:35] this Bean required interception it
[57:37] create a proxy of
[57:39] it now if you go now I am proceeding
[57:44] further now proximity created to either
[57:48] jdk dynamic or cgli so this is the third
[57:52] part
[57:53] right so this one I haven't taken
[57:56] screenshot but the proxy here you can
[57:58] see in the code itself either here if
[58:00] you see that jdk Dynamic aop proxy or if
[58:05] in Target class do it is interface there
[58:08] is no interface at all it goes for cglib
[58:11] aop
[58:13] proxy okay so till now what we have done
[58:18] is and after
[58:20] this I'm running
[58:23] again so currently my class employee

## Chunk 53

[58:26] util doesn't have any interface so it
[58:27] goes for
[58:28] cglib and here if you see that
[58:30] application startup happen
[58:32] successfully
[58:34] okay so till now before application
[58:37] start up it's clear what it is doing it
[58:39] Parts the point
[58:41] cut now after that when it is uh
[58:44] creating the bean during application
[58:46] startup for each class if it required
[58:49] interception it create a
[58:51] proxy so which proxy either jdk proxy or
[58:56] uses cglib based proxy but it uses any
[58:59] one of the proxy and create a proxy
[59:02] class now for at this point of time
[59:05] there's something called employee util
[59:06] atate some random number now this is my
[59:09] proxy class which is now a child of
[59:12] employee
[59:14] util and it has overed that method
[59:16] whatever the method it had overed it
[59:19] which required interception and now it
[59:21] has written some code over there
[59:23] generate code

## Chunk 54

[59:27] now I am invoking the request which need
[59:30] advice to be run now I am invoking this
[59:32] API so controller now I am invoking this
[59:36] method at this
[59:39] point now what will
[59:41] happen so here if you
[59:45] see now let's see I am invoking a method
[59:48] so now here I am
[59:51] hitting okay so now what would happen
[59:53] here at this time
[59:56] we'll see that it it would have come
[60:00] here and then call employee util do
[60:04] fetch employee method now if I go
[60:06] inside now it will
[60:09] check at the point of application
[60:12] startup for this employee util because
[60:15] this is applicable for interception
[60:17] there is one proxy class created for
[60:19] this employee util proxy right so
[60:22] internally that proxy class might have
[60:25] invoked not this class involved that
[60:27] proxy class got involved
[60:30] because here if you see that my
[60:34] aspect it matches it matches with this

## Chunk 55

[60:37] uh employee U right it matches with this
[60:41] so this class required interception and
[60:42] during application startup employee util
[60:44] at theate something a proxy class have
[60:46] created so that proxy class have created
[60:49] we can't put debuger point in that proxy
[60:51] class because that is dynamically on fly
[60:54] that proxy class is created
[60:56] and in that proxy class what it does it
[61:00] it
[61:02] invoke
[61:03] your intercept method inside cglib aop
[61:08] proxy so here if you see inside
[61:12] cglib it will invoke this intercept
[61:15] method why cgli because employee util is
[61:18] not a child class of any so that's why
[61:20] cgli proxy have used at this point of
[61:24] time at this point of time
[61:27] this so This proxy might have been
[61:30] used so that's why that employee util at
[61:35] theate some proxy class have got invoked
[61:38] and it has called this intercept
[61:41] method now see this what this intercept

## Chunk 56

[61:44] method is
[61:45] doing there you will see that it is
[61:48] creating a chain of
[61:51] advice right so now let's say that this
[61:55] method which we have to invoke there are
[61:58] let's say
[62:00] five point cut which are
[62:03] matched so there is a list of Point Cuts
[62:06] or advice now which has to be run for
[62:09] this some could be before some could be
[62:12] after or some could be around which has
[62:14] to be run but this five got matched with
[62:17] that particular method okay so now I
[62:20] have created a chain not I the jdk
[62:22] library I have has created a chain now
[62:25] now what would happen is that it is
[62:28] calling do proceed method so this
[62:31] proceed method
[62:33] goes to this reflection method
[62:37] invocation this
[62:39] proceed so now here if you see that it
[62:43] has
[62:44] counter so now let's say it has to run
[62:47] five advice right so it will go 5 4 3 2
[62:51] 1 and after all the advice method

## Chunk 57

[62:54] invocation has happened
[62:57] okay but there could be some before
[62:59] there could be some after so how it is
[63:00] handling this I will tell you so
[63:03] currently index is uh zero no index is
[63:07] not zero what happen is it will go
[63:09] inside this else
[63:11] part okay so now let's say we have two
[63:14] advice right I showed you we have before
[63:16] and after here in the code I have showed
[63:19] you the uh aspect which I have written
[63:23] one is before and one is after which
[63:26] matches
[63:28] this okay so in the chain I have two
[63:31] counter is
[63:33] two right so now so it's starting with I
[63:36] think it is starting with Plus+ so it is
[63:39] starting with uh 0 1 right then it is
[63:42] matching if the counter reaches to the
[63:44] end so first let's say before is coming
[63:48] so now what before is coming what it is
[63:50] done is it is
[63:51] invoking so for before there is a it
[63:54] will invoke a method so first so first

## Chunk 58

[63:58] call when it is calling Interceptor
[64:01] method Interceptor right so before it
[64:04] will call method before advice
[64:08] Interceptor so this invoke will get
[64:10] invoke and here it will say that it will
[64:12] run the advice first advice do before it
[64:15] is running the advice first okay so this
[64:19] advice is running before so it will
[64:23] print inside before method X expect
[64:26] now so this has
[64:30] printed inside before
[64:33] method accept at this point at this
[64:37] point now again it called do proceed mi.
[64:42] proed method invocation do proceed so it
[64:44] goes back to this
[64:47] method now again the counter has already
[64:50] reached to the Plus+ so it become one
[64:53] now again it hasn't reached to the end
[64:55] so what happen is it goes to the else
[64:58] part now again this again calls invo but
[65:02] now for the after
[65:04] one it will call
[65:07] third this Interceptor aspect J after

## Chunk 59

[65:11] advice because now the advice is after
[65:14] so it will call this Interceptor call
[65:17] this invoke method now after is like
[65:20] after the method advice should run so
[65:22] that's why here it say that it
[65:25] calls the back so now it is doing kind
[65:27] of a recursion way if you know recursion
[65:29] you can easily understand this it calls
[65:32] the proceed again hey you proceed
[65:34] further and once that proceed happen
[65:37] then come back and run this advice after
[65:40] okay so now it goes up
[65:44] proceed fourth it again goes to this
[65:47] proceed now control Plus+ it already
[65:49] reach two so now this become equals now
[65:53] here if you say that it is invoking the
[65:54] joint point I I already told that join
[65:56] point is a point where the actual method
[65:59] invocation happen now it is actually
[66:02] invoking the method so now it is
[66:04] invoking so currently this after advice
[66:07] it is will run currently it is in this

## Chunk 60

[66:10] part so currently this is
[66:13] running and when this is running invoke
[66:16] joint point so fifth step this method
[66:19] invocation will happen so this method
[66:22] invocation actually happens means
[66:27] this employee U this will print fetching
[66:30] employee details will get
[66:32] printed so it will
[66:38] print fetching employee
[66:42] details so this fifth is also completed
[66:44] when this is completed and it returns so
[66:47] it returns from where it comes so it
[66:48] comes from this so after that it will
[66:51] run so this will return now invoke
[66:54] advice after one so now after advice
[66:57] will run right so this is your actually
[67:00] the sixth after advice so after advice
[67:03] will run
[67:04] means this is the
[67:07] after inside after method
[67:12] aspect inside after method aspect so
[67:16] this will get printed like this so this
[67:18] is your actual method which you wanted
[67:21] but see before and after advice run

## Chunk 61

[67:27] and how I told you right so here if you
[67:29] see that currently if I debug it so
[67:32] currently it is running inside
[67:34] reflective method invocation so first it
[67:37] is running
[67:38] before so it will come under
[67:43] your method before advice Interceptor so
[67:46] once it has printed the advice by now
[67:50] and then it call
[67:51] proceed then again this method has been
[67:54] invoked
[67:56] then again this method has been invoked
[67:58] now it will goes to uh after now in the
[68:02] after it will first call
[68:04] proceed and then it comes to this uh
[68:07] method so it will again goes to that
[68:08] method now it
[68:10] will now it will call this actual
[68:14] method now it will call the actual
[68:16] method here now it say that uh actual
[68:18] method has been invok inside the employe
[68:20] util now after actual method it will go
[68:24] again back to the advoice uh finally
[68:26] part where the advice will run and
[68:29] finally it will

## Chunk 62

[68:32] print if it see the
[68:35] console before employee and after if any
[68:39] doubt we can discuss further and uh I
[68:42] hope you will like it please do share it
[68:44] with your friends who really confused
[68:47] with the proxy and the aop part thank
[68:49] you thank you bye

