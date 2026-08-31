0:00
Hey guys, today we're going to explore Redis. I'll try to cover Redis completely in this video. But if something is left out or becomes too long, I'll create separate videos for it. You'll get a complete playlist and the playlist link will be available in the description of this video. So make sure to check the complete playlist there. Also, if you haven't subscribed to my channel yet, please subscribe now. First, let's look at the introduction to Redis. What is Redis? What exactly is Redis?

0:23
Redis is an open source BSD licensed in-memory data structure store used as a database, cache, message broker, and streaming engine. So Redis is an open source product that follows the in-memory data structure store principle. This means whatever data we store in it will be stored in RAM memory, which is why it's very fast. Traditional databases like MySQL and PostgreSQL are much slower than this. Redis is used very extensively, and I'll show you which companies use it. So Redis is an open source product that follows the in-memory data structure store, meaning whatever data we store in it will be stored in memory. You can use it as a database, as a cache, as a message broker, and also as a streaming engine. Redis is written in C and works on most POSIX systems like Mac, BSD without any external dependency.

1:30
Linux and OS X are the two operating systems where Redis is developed and tested the most, and we recommend using Linux for deployment. So, how to install Redis in your product? Whatever product you build where you'll use Redis as a database or as a cache, then there...

2:00
won't be a problem. Your application won't work. Here's a list of well-known companies using Redis, such as Twitter, Amazon, Snapchat, Netflix, GitHub, and many others use Redis as a database or as a cache. Now let's talk about how to install Redis. How to Install on Ubuntu (Theory)

2:51
There are many ways to install it, but I'll tell you some methods. You might need to update the repository first. After updating, you'll need to run some APT update commands, then apt install Redis. For system installation, you'll use these. Then to check the status, you'll use these. Then if it's not enabled, to enable it, you'll use this. To start it, you'll use this. To stop it, you'll use that. And to restart the service, if you need to restart Redis, you'll use this. Sometimes some commands work on some systems, some don't, or they might not work on Fedora. That's why I've written everything, so you can try which one works on your system. So I might work on Ubuntu, might not work on CentOS, or might not work on Fedora. That's why I've written everything. You can try which one works for you, whether it's disable, stop, start, or enable.

3:45
You can also disable it. There's a disable command too. Instead of enable, you just write disable. Apart from this, there's a snap way. With snap, you get it by default if you want to install using apt install, you can do it like this.

3:59
You can also use snap.com to install it. Then after installing Redis, you can check the version like this.

4:35
So there's one way, and another way is simply using snap. If you use this, then you can install it. That's all you need to do, because snap will already be in Ubuntu as far as I understand. Here we'll have snap ready, so you can use this too. In this way, you don't need to do curl or anything like that. So you can use either method. These were for Ubuntu. I told you this earlier. They said you can do this too. There's no problem with both, but then the commands will be different for both.

How to Check Redis Status

20:27
snaptest.org In some cases, some commands might behave differently. Let me show you once. Like here, with sudo, first let me check redis-cli --version to see it here.

20:38
I'll check the version, and you'll see 7.0.1 for me. Let's clear this and check the status. How to check the status? You'd use sudo systemctl and status of Redis, then press enter.

20:44
Like this. Let me press the enter key and check.

20:51
So systemctl status redis and active is running here. It might be active, meaning it's active and you can see it running here. Sometimes what happens is it won't work like this. Instead, you'll need to write here, you'll need to write redis-server redis-server, then press enter.

21:09
You'll see the same output here. Apart from this, sometimes you'll need to write redis.service. So redis with the service also works now, so you should definitely try it once with your operating system. All three commands are working for me, so any one of your commands will work, which is specific to your operating system. But I've shown you all three. Similarly, you'll first enable it. Enable Redis

21:34
Let me check the status first. If it's running or whatever, then run the enable command. Let me press enter here.

21:39
You'd write sudo systemctl and then enable and Redis like this. Let me press enter and see. My disable to enable is refusing to operate on alias name and link unit file. So this enable command isn't working just by writing Redis. I'll try writing redis-server here. Let me try. It synchronized this time and this one worked for me. So this is how issues will occur that you'll need to fix. Sometimes the server won't work either. You'll need to write redis.service like this. So you'll need to check which one works for you. Okay, I showed you how to enable it. Now I need to disable it. Disable redis

22:19
So you need to write systemctl and disable. With this your Redis will be disabled. Or instead of redis, it could be redis-server or it could be redis.service. I try just writing redis, then it says it's been removed. Look, it removed it and my disable is complete. Now let me check the status and see what it says. It checked the status and look, it can't tell me the status anymore. Or if I check with the other one...

22:44
So I don't know what to do. I need to enable it. sudo systemctl and then enable and I need to write redis here. This will work with just redis, so that's good. If not, then I need to write server, server, then press enter and see. It synced and our systemctl and a symbolic link was generated, etc. Now if we check the status again, it will tell us that it's active and running. Okay, so we checked the status, learned how to enable and disable it. Now let me teach you how to start it. sudo, then you need to write systemctl and start and write Redis here.

23:14
It could be redis-server here or redis.service here. Okay, let me press enter and this will start for us. It was already started, but we started it anyway. Now if you want to check status, you can check status. We'll see it's active and running. Similarly, if you want to stop it, you can stop it too. Instead of start, you'd write stop and press enter and this will stop for us.

23:31
Start and Stop redis

23:36
Let me check the status now. It will show as inactive. Now I need to exit from this and start it again. To start, I need to run the same command as before, systemctl start. This will start. Let me check the status again and it will be active and running. Now we've seen status, enable disable, start and stop. Now only restart is left. Let me go here and restart is all you need to write instead of status, and press enter and it will restart.

23:54
Restart redis

24:01
Whenever you make changes to the Redis configuration file, you'll need to restart your Redis. That's why this command is very useful. So I've written all this in the PowerPoint. I've written everything in the PowerPoint and I've also added a note that you can use Redis or redis-server or redis.service like this. So you'll try all three and I've shown you everything practically here. Now I'd like to check one thing here, let me try sudo service. So with sudo, let me write sudo service and Redis restart and press enter.

24:34
Look, this is also working for me. So if you want to use service, you can use service instead of systemctl. Let me check the status to get a better output. So let me clear this first and then you'll see differently in front. Look, let me clear it so you can see it better in front. Look, here's what you need to do. You'd write sudo, then write service, then which service, then Redis service, and what do you need to check, status. So you need to write status. Instead of status, you can use enable disable and start stop, restart all these. So with service, you'd do it this way. If you want to do it with CTL, you'd do it this way. sudo systemctl restart here you need to write first and the name of the service, which is what you'll write last. This is when you use systemctl. And when you use CTL...

25:10
If you're using CTL with systemctl, then if you write Redis, you'll need to try it first. If it works from this, great! If not, then try writing server. If it works, great! If not, then try writing service.

25:28
One of all three will definitely work. I've seen this before. So that's just it. Here in this, what happened is that when you normally install it, all the commands like start, stop, enable, disable, restart, status check is how everything works. Now I'll show you...

25:42
I'll uninstall it and show you that...

snap doesnt give redis.conf file

25:58
I've done all that and we've run all the commands. Now let me show you...

26:08
That happens with snap.com, you don't get access to it directly. Meaning you don't have full control over the configuration under snap. At best, you'll get control of the configuration from here. You won't have full control over the configuration file for yourself. So if you want full control of the configuration file under you, then you'll install it this way. Otherwise, you can use this method. This is simple and easily does our work. So I'm also going to show you this. I'll use this for a while, but later I'll uninstall it and run it on this one when I need the configuration file.

26:42
Okay, so for now this is the situation. But maybe later snap will give you full configuration control. That's a separate thing. I don't know what will happen in the future. So these two approaches, Windows installation, and Install Redis from source.

27:05
I'm showing this. If you see in Windows, you'll get WSL here. With WSL, you can install it this way. Here they've written Ubuntu's installation would be the same. Just follow the same process. Here they've written redis-server. It's written with service. That's a good thing. And all these things are given here. So WSL, I've already told you how to install it in Windows, how to enable it, and how to do everything.

27:22
How you can install it with DEB or Dan. Here
And you can run this Redis in Windows this way too. But what happens...

Install Redis using snap

27:44
[Music]
I copied this. After copying, I need to come to the terminal. I want to run it on root. It went to root. In root. You can also work from a regular user, you just need to add sudo to every command. You'll need to add sudo, sudo. But here's mine. In this, I'll paste it. This is sudo snap. Snap will already be installed from before, so...

28:04
snaptest.org This will download. Look, it has downloaded. After that, it will fetch and then it will start installing and setting up. And this Redis has been installed for us. You can see it's installed very easily with snap. So this Redis 7.0.1 has been installed for us. Now how will you check it? You'll check it like this. redis-cli --version. Let me press enter.

28:41
Look, you won't see it this way. Because this doesn't have redis-cli. This has redis.cli --version. Then you'll see it.

28:46
Okay, so remember this. This has a dot, not a dash. In many places, you'll see dashes. If you install it this way, then you'll get redis with dashes.

28:53
Set redis-cli alias

29:05
You can set an alias. Like I told you earlier. If I show you an alias right now. Then you need to write sudo snap aliases and turn redis.cli into redis-cli. Now press enter and...

29:11
It's been set for us. Now we can use redis-cli -version in this too.

29:17
Then it will work for us too. Okay, so this is how you set some things. We've set this. Now let me check our status, etc. to see if everything works.

29:29
Start, Stop, Enable, Disable and Restart Redis

29:29
So here we'll write sudo snap and then check status. And you need to write status and Redis. Let me press enter. Okay, this doesn't have status I believe.

29:37
Let me clear this and try starting. sudo snap snap, I need to write snap. snap start redis. Let me press enter. Look, it's started. It's started. You can enable it like this. So

30:03
sudo snap snap I need to write snap restart and Redis like this and this will restart for us. Restart anytime you make any changes to the configuration. Then you restart Redis and you'll see the effect.

30:24
Apart from this, there's sudo snap services that shows whether it's enabled or not, whether it's active or not. So instead of status, you can use this. This tells you that redis.server is enabled and active and there's a desktop integration showing here. Okay, so it's working great. So Redis server is running for me. Now if I want to go to redis-cli, if I do redis-cli, it will send me to this CLI. This is its local host, meaning the host is localhost and this is its default port 6379, and now I'm inside Redis. Now you can run Redis commands here.

31:04
But this will only happen when your Redis server is running properly. So our Redis server is enabled, so it's running in the background. To check this, you can ping here. Ping. This will give you a response. Pong. If you get ping and pong, then understand that your redis-cli is working properly and you're ready to run commands in it.

31:16
PING

31:22
String Data type Commands

31:22
So first I'll show you strings. String data type. We read that in theory. I'll show you its commands. Like the first command here is KEYS. With this you can see which keys you have. So we don't have any right now. We have an empty array.

31:33
If you want to set a key, then write SET, then write the key, then write the value. It tells you here in a nice way. So the key and value. I gave it the key "raj" and "raj". Let me press enter and it will give you an OK response. Meaning you've set a key with the name "name" but you can give it any name too. If you want to get it, then you need to write GET key. Then it will give you "raj".

31:39
If you want to give it a different name and a different value, look, I write SET and here I give the name "Suhani" and press enter.

31:45
So now I have two keys, one key named "name" and one named "name". So you can do this too. I'll show you if you GET the key, then it will give you "raj". But if you GET name, then it will give you "Suhani".

31:51
Okay, so SET and GET you've learned. Now let's delete. Say I want to delete this key "raj". It's specific, so write DEL and the key.

31:57
So this key "raj" will be deleted. But "name" will remain. So if you try GET key now, you won't get "raj", but you'll get nil. But if you GET name, then you'll get "Suhani". So that's it. You learned to SET, GET, and DEL.

32:03
You can also check if a key EXISTS. Check if this key exists or not. Like if I check for name, then it will tell me. One means it exists. If I give a key that doesn't exist...

32:10
If you give a key that doesn't exist like "role", then it will give you zero as a response. Because "role" we don't have. Then if you set it, like if I set "role" to 10, now it exists. So now it will give you one as the response.

32:17
Okay, so that's how you can check if a key EXISTS. Besides, you can write the key name like this. SET user:1 and here you can write the value. Or you can write it like this. SET student:1 and here you can write. Or like this. student:1. And here we'll write. You can write the key name like this. Then you can SET like "student:1" and here write the value. Like "Rahul". So you can write like "user:1" and here write. Or you can write like this. Say if I SET the key. Then if I GET, then I'll get it easily.

33:09
Now if you want to set multiple keys at once, that's also possible.
MSET is like SET. And now if you want to set multiple keys all at once, you can use MSET. So how does MSET work? It takes pairs of keys and values. It takes key-value pairs one after the other.

38:35
So you can write MSET name Raj role 101 and class 9. Like this, you write. Press enter and then you can CHECK. Let me see the keys.

39:02
OK, so MSET is done. You now understand MSET versus SET. What's the difference? The difference is that SET will overwrite. If you already have a key, then this one will create or update. MSET is like SET but for multiple key-value pairs.

40:51
So there are some basic commands. These are very easy commands. You can use them. Besides that, there's a lot more. But this is the basic stuff. If you want to specify a key, then if you don't want to overwrite, then for that you get a different command. This is SETNX. If the key already has a value, then it will ignore it. If not, then it will create it.

41:02
So this is the command to not overwrite. Besides this, we have DEL to delete. It returns the string value of a key after deleting. After deletion, it returns that. This is also good. You can GET with GETEX. You can GETRANGE. If you need to return a substring, then you can GETSET. Here, you can see much more is not available. But this is the maximum I told you. What's left here, you can read it from the documentation.

43:46
After strings, let's see LIST data type commands.

44:03
List data type Commands

44:03
Let me see the documentation here. Here from the list, I'll select. Here comes LPUSH. Let me see LPUSH first. Look, what is LPUSH? LPUSH inserts all the specified values at the head of the list. If the key does not exist, it creates it. If the key exists but doesn't hold a list value, then an error is returned. It's possible to push multiple elements using a single command call. Just specify the arguments at the end of the command. Elements are inserted one after the other to the head of the list.

45:03
From the leftmost element to the rightmost element. So for instance, LPUSH A B C will result in a list containing C as the first element, B as the second element, and A as the third element.

45:16
So if I run the command now, I'll write LPUSH and here I'll give a key, then this in multiple values. Like I said A B C. So it will contain C as the first element, B as the second, and A as the third. Like if you give A then it becomes the first. B then becomes the second. And A becomes the third. So what you give last becomes first and what you give first becomes last.

45:46
It returns the length of the list after the push operation. Look, here they've given LPUSH my_list "world". So one came. Now LPUSH my_list "hello". So two came because on the same list, two words came.

45:58
Then LPUSH my_list 0 1 will give the range. So here it will display the entire key in the list. So here I'm showing you a little bit so you get the habit from here. Otherwise, understand that I've described it here. But you didn't come and see, so I don't think anyone will understand.

46:10
So let me show you. It will take some time but there's no problem. I LPUSH'd a key. Let me take a key like students. And here I'll write the name of students. So I'll write "Suhani" as a student name. I can write it like this. I can give a single value. So I wrote "Suhani". Let me GET it. There's no GET in this. There's LRANGE. Okay, so remember. So I'll do LRANGE with this students key. And here I can look where to start. LRANGE it from 0 to 1. Then it will give you that specific range.

46:38
If I want to see everything from start to end, then I can write 0 and -1. So it will show you everything. Now you can see the entire content of this key.

46:45
Now let's LPUSH again. Like I LPUSH'd with the same key students. This won't overwrite, but it will PUSH one after another. Let me LPUSH one more. Like I LPUSH'd "Raj". So PUSH happened.

46:52
Now two of them we're looking at. That means two LPUSHes have happened. Now I can see with LRANGE. So let me do LRANGE from 0 to 1. So you can see here 0 and 1. Now let me LPUSH again.

47:04
If you want to do multiple values at once, then you can do that too. Let me LPUSH and write students. And here I'll write "Rahul", "Rani", "Soni". Like this. I wrote. And press enter. That's five for me. I did three and two before, so now let's range and see what happens...

47:34
Remember, "Suhani" was the first, so she's at the bottom. Then we did "Raj", so "Raj" is above "Suhani". Then we did "Rahul", so "Rahul" is here. Then we did "Rani", so "Rani" is above it. And then "Soni", so "Soni" is above it. This is how it's being inserted.

47:52
If we FLUSH all, then this will disappear. If we see the range, then you'll get an empty array. So let me clear this and LPUSH again with students. And let me write "Rahul", "Suhani", "Soni", "Raj" and "Rohit". And press enter. Five, I've done in this. Now let me see the range.

48:02
So all five will show. So we gave "Rahul" first, so he's at the bottom. And what we did last is at the top. Otherwise, you can see the adjustment. This is the important thing to keep in mind.

48:22
But you can define LRANGE in this. Like if I do 0 to 1, so you can see. So 0 1 2 like this. So you'll only see 0 0 1 2 like this. So "Rohit", "Raj" and "Soni" will show. If you only do 0 to 1, then you can LRANGE from 0 to 1.

48:35
Then you'll get "Rohit" and "Raj". If you do 0 to 0, then this is 0, this is 0. Then this is 1. Then this is 2. Then this is 3. Then this is 4. Like this. So if I do 0 to 4, then I'll get everything. 0 to 4 fits perfectly for us.

48:47
Okay so that's how LRANGE works. And we also have LPOP. I'll show you LPOP. So you can POP.

49:06
LPOP removes and returns the first element of the list. So the first element will be removed. If we LPOP now, then let me write LPOP and the key.

50:10
The key is students. So this will set you in LPOP. Enter and then you'll see. So let me clear and then check LRANGE. And you can see me delete from the beginning.

50:16
Look, I LPOP'd. Enter and "Rohit" came. So LPOP. The first to beginning removes one. If you give count here, like I gave two. Then if you press enter, then it will LPOP two elements. So the number of elements you want to POP. You write here.

50:27
Let me see the range. So we have "Suhani" and "Rahul" left. Otherwise everything has been removed.

50:36
If you want to know the LENGTH, then LLEN and the key. The key is students. Then it will tell you how many elements this has.

50:41
Two is so it says two. If you want to know the value of a specific index number, like you want to know whose is one, then you can...

50:47
What can I do? For that, you get LINDEX and here you need to write the key. So the key is students. And which index number? Let's say I want to know one which is Rahul. So one is here. Four, no REPLACE.

51:00
You'll get Rahul. If you write 0, you'll get Suhani. So if you want to know the specific index value, you can use LINDEX like this. Otherwise, you can SET a specific index. Here's LSET and here you're giving the key. The key is students. And which index are you setting on?

51:12
Like I gave 0 and here I gave a new value. So if that index already exists, then it will overwrite. If it doesn't exist, it will range out of range. So let me first look here. I have Suhani at index 0. I'll delete it and change it to what? Sonam. Let me press enter and see. OK, it's done. Now if you want to check it...

51:24
You can look at the index. Look, Sonam is at your index. You can also LRANGE too.

51:30
LRANGE you...

51:36
Look, Sonam and Rahul are done. Now let's give an out of index. Let's LSET on an index that doesn't exist. I gave 4 and I'm setting a new name. I wrote Raj. Press enter and it will tell me. Index out of range. So the range should exist. When you use LINDEX, when you use LSET to set some value at a specific index, the index must already exist and it will replace it. This is also something to keep in mind.

52:04
So it's done. What if we DELETE it? If you want to delete, you can FLUSH all. Write this and your database will be cleared.

52:10
OK so now let's start from scratch and LPUSH the students key and students and now instead of students, I'll write user_id and write 1 2 3 4 5 6. Press enter. You'll get six here.

52:16
And if you check LRANGE, the key is user_id. Start from 0 and you'll get the entire range.

52:22
From 1 to 6. One was given first so it's at the bottom. Six was given last so it's at the top. That means row has this index, one has this, two has this, three has this, four has this, five has this. That's how indexing is done for it.

52:30
Then there's LPUSHX. This does what? Let me give an example. Let me check. Here I'll write 7 8 9. Press enter. It will set in it. You can check in LRANGE. See, 7 8 9 is now set here. So LPUSHX...

52:36
And LPUSH, what's the difference? Both are different. Both the difference is that this LPUSHX works when this key already exists. The key must already exist for this to work.

52:42
Otherwise it won't work. Like now if I LPUSH with students, I write students and here I write "Suhani", "Rahul" and "Raj". These three I gave. Press enter and it'll give you zero. See, in LPUSHX, you can't set up any list.

52:50
Let me show you the LRANGE. It wasn't working. LRANGE shouldn't work on this key. It already exists for user_id. So let's check.

52:58
LRANGE user_id 0 -1. Then you can see this range. Now I want to INSERT at a specific location. If you want to insert at a specific place, how would you do it? You'd use LINSERT. LINSERT.

54:04
You need to write LINSERT, then the key. The key is user_id. What to do, BEFORE or AFTER. So here you can write BEFORE or AFTER. Write whatever you want. If I write AFTER, then see I wrote AFTER. Then here the pivot is here. Pivot means at which element you want to do it.

54:15
Like if I want to do after "Suhani", then I need to write "Suhani". And what to do? Here I need to write "Rohit". Then I wrote Rohit. Press enter and five becomes six. Now let me see the entire RANGE and you can find "Rohit" after "Suhani" here.

54:22
That way BEFORE. So if you want to see BEFORE "Suhani", you'll see BEFORE. So besides that, I showed you everything that happened with L. That same thing happens with R as well. There's RPUSH, RPOP, and there's R and the things from R. Then there's LSET with LTRIM and all that. You should see it.

54:38
Otherwise let me see the L... LINDEX exists. LINSERT exists. LLEN exists. LMOVE exists. LMPOP exists. LPOP, LPUSH. All these you'll see and beyond that...

54:50
Come back here. You'll find R here too. There's quite a bit. So if I find R...

55:03
Look, RPUSH is here, RPOP is here, R... This is there. Then RSET is there, LTRIM is there. So see all these things. And I'll show you one RPUSH one RPOP to you, so that you also understand.

55:13
Let me clear this from the front and FLUSH all to get rid of everything. Let me FLUSH all to clear everything. Now let me start RPUSH. Let me write the RPUSH key here. I'll write frameworks. Frameworks frameworks. Let me write here the frameworks frameworks.

55:28
Let me write Django and Laravel and Express.js and like that. Let me just give this much and press enter. You'll see it here. Then you can see LRANGE.

55:38
Oh wait, there's no LRANGE. I should write LRANGE. The key is frameworks. And 0 and -1. Press enter and now you can see. Look, what happens here? What comes first is first. So the LPUSH and RPUSH difference is that...

55:54
What comes first is first here and what's last is last. So the LPUSH and RPUSH they differ in that LPUSH and RPUSH difference.

55:59
Where you LPUSH from and where you RPUSH from. So it comes first, so it's first here above. Then it comes here, so it's here after that. And then it comes here, so it's here after. Like this. So the one that came first is at the top in this list. It's at the top here.

56:05
Otherwise, that's how LRANGE works. There's nothing to do in this. The documentation I showed you. There's nothing in it either. So you look there. I also showed you that if RPOP is future, then everything else is the same. LRANGE to see.

56:16
Here's just two "Django" and "Laravel". The rest are only "Express" gone. The other things you saw in the documentation, I showed you. So LPOP...

56:22
LPOP, RPOP, LPUSH, LRANGE... I taught you. Now let's see lists. There's also LPUSHX. I show you again. So basically LPUSH and RPUSH, LPOP, RPOP, and everything else is there. LSET is there. LTRIM is there.

56:38
We'll look at it. Otherwise, first, let me clear this and see...

57:13
Set Data type Commands

57:13
Now let's see SETS. What are SETS? SETS have unique elements and it's unordered. First let me show you the official talk. Here I need to come.

57:18
And from here, SETS. Here I need to come. Look, there are so many commands here. Out of these, I'm going to tell you some now. Like SADD will tell. SMEMBERS will tell. What does SADD do?

57:24
SADD adds one or more members to a set. Creates the key if it does not exist. SMEMBERS what does it do? Returns all members of a set. So to see all members, you can use this.

57:30
Then SISMEMBER. Determines whether a member belongs to a set. That means whether this member belongs to a set or not. You can use SISMEMBER to know.

57:42
Then SCARD. Returns the number of members in a set. How many number of elements, how many are there or... members it's called here in the set.

57:55
So in the set they're called members and it will tell you how many. Or members it's called. In the set, it's called members. Then it will tell you the difference. It tells you the difference and stores it on one set.

58:00
And there are many here. MOVE is there. SPOP is there. SUNION to extract. You can extract union. INTERSECTION too, if anywhere there'll be intersection. Look, there's SINTER. SINTER doing intersection. Apart from this there's SREM to remove.

58:06
And here from you'll get good information. Much here we look and do our work. So let me clear all. FLUSH all.

58:24
I've done FLUSH all. Let me check once more. And here let me check...

58:30
SADD, we can do this. You can also write it in capital. Some people write it like this. It's a capital letter. But I write it like this because with caps it takes time. I can turn caps on or off so it takes time. SADD let me write sets. I don't write sets. I'll write here, let me open, open, I write open and open or write token, write token.

58:41
Unique is here. Okay, so I write it this way. Then user_id. Let me also write user_id. User_id is also unique. So I wrote user_id. Let me write 101. This is the first member. 102 this is second. Then 103. Then 104. Press enter and four.

58:52
Our user_id set is done. So we've created the set. Now here I need to look at this. I need to write SMEMBERS SMEMBERS and the key is user_id.

58:58
So it will show me 101 102 103 104. So this is how you create a set. And this is an unordered collection. And it's unique. It's unique. What does this mean? This means what? It means to understand. Let me clear this.

59:05
FLUSH all now you'll see SMEMBERS. So nothing is there. It's empty. OK now let me reset. So here I give one more 101. And one more 103.

59:12
Let me see what gets inserted. Let me SMEMBERS. Let me see what gets INSERTED.

59:19
Only four were inserted. While we gave 1 2 3 4 5 6. So whatever duplicate, the duplicate is eliminated. Means if you see SMEMBERS...

59:26
SMEMBERS, what did I give? Here I saw 101 102 103 104 and one more 101. One more 103 there. So the two times instead of doing twice, it only does once. It eliminates the duplicate. So this means only unique members. Will be taken. It won't take duplicates.

59:45
So this is a very good data structure. Or data type. Where you can put user ID or token coupon discount voucher this kind of things. If you want to adjust, you can. Like maybe a coupon shouldn't be a duplicate. And one user shouldn't use one coupon twice. And not the same coupon be generated twice. The same coupon number shouldn't be generated twice.

1:00:06
That's because you'll keep track of it. Now SCARD, let me look at this. You, user_id, this will tell you how many members in the set there are. Information about that.

1:00:16
You can also count. If you want to count the ones here. I'll show you. So look, this is 12. So half divide it, you get six. This is one, this is two, this is three, this is four, this is five, and this is sixth. That's how you can use SCARD and the key. So this will get you. How many members or number of elements in the sorted set there are. Now if you want to remove from this... SREM, you can use SREM. I'll write the key here. User_id and which member. Do you want to remove? Let me say I want to delete 101. So I wrote 101. Now press enter and one. One is removed from here.

1:00:55
So you can see, 101 has been removed. So whatever you want to remove, you can give. And it will be removed from it. Easy. So you can specify exactly which you want to remove. If you want to randomly remove any member from this, then you can use SPOP. SPOP is user_id and...

1:01:01
And press enter. A one is randomly removed. If you give a count value here in SPOP like I gave two. Then that many members will be randomly POPped from you. There's not much left for me so I won't do that. But you understand. That this is possible.

1:01:27
Let me FLUSH here. FLUSH all. I'll remove this and create a new one. SADD results_one and here I'll write one 2 3 4 5 6 and until 5.

1:01:40
I'll give this. Press enter. This will become one. SMEMBERS let me see what we had. RESULTS one. You can see one to 5. This is in results_one. Same way create one more set. But here we'll name the key as results_two. And I'll give 3 4 5 6 7 8 9 na this is given. Press enter. It has seven in it.

1:01:52
So results_one has these and results_two has these.

1:02:00
OK, I'll do a DIFF. The difference I can see. Like SDIFF. I write this. Here you give two keys. More than two you can give. Like here I'll give results_one and results_two.

1:02:07
Here you can see what difference there is. What difference there is between results_one and results_two. Now results_one has one 2 3 4 5 6. Results_two has 3 4 5 6 7 8 9. But the difference it finds is only two. Let me show you how it does this.

1:02:14
So here look SDIFF results_one and results_two. So it compares this entire thing with this entire thing.

1:02:21
Now what matches in this? 3 4 5 so 3 4 5 are matching. So what it does is it ignores 3 4 5. And 1 2 are the rest not matching.

1:02:28
So SDIFF results_two results_one. Then me output would be like 6 7 8 9. Because when you compare this entire thing with this entire thing...

1:02:35
So what matches? 3 4 5 are matching. So it ignores. So the rest of this which don't match. 6 7 8 9. So this is the difference. First what you write. Its value. What's different. That you get output.

1:02:41
So again, if I reverse it. Difference find. So results_two compared with results_one. So compare this with this.

1:02:51
And when you compare this with this... So what matches? 3 4 5. So you leave those aside. So what's different from this compared to this? So you'll get a 6 7 8 9. So this is how it finds the difference in this.

1:02:58
Now when you compare results_two to results_one, you'll get 6 7 8 9. So how many's the difference?

1:03:05
So SDIFF results_one results_two. Then SUNION where you get difference 1 and 2.

1:03:11
Then you'll get output 6 7 8 9. That's if we reverse it. Two and one then you'll get 6 7 8 9. So UNION operation. Let me change to what's happening here where I do UNION.

1:03:16
Let me now do SINTER. Let me do SINTER. Let me do SINTER results_one results_two.

1:03:35
So results_one has one 2 3 4 5 6. Results_two has 3 4 5 6 7 8 9. So now what's the intersection? Let me see. Here you see. Results_one has 3 4 5. Results_two has 3 4 5 too. So only 3 4 5 are common. You look. So that's your result.

1:03:50
Now if I reverse it. Two to one. Then it's also 3 4 5. Because intersection works like that. Those which are common in both sets.

1:03:56
Now let me store this somewhere. Like if I do SUNION results_one results_two. Then if I do SUNION, then if I store it, then I do it. But you forget to remember. So now SUNION STORE...

1:04:10
Let me do SUNION STORE here. I'll give a destination key. You give any key. Like I'll write final_results_one. And you'll look at results_one and results_two. Here results_one and results_two. SINTER actually no, SUNION.

1:04:16
And press enter. Nine was stored. Now the entire set. So we have SUNION here. And you can check this. SMEMBERS and final_results_one. This full union you'll get. Similarly, there's SINTER STORE for intersection. Write SINTER STORE. Here you give any key. And both. You'll look at. It'll store and make intersection.

1:04:33
So that's what happened. Now let me just to be safe at LLEN. I'll take SMEMBERS. Let me do this to be safe. SMEMBERS user_id? Final_results_one...

1:04:42
Let me do SMEMBERS final_results_one. And now so this full union you see. Besides, if you've done SINTER, you can find difference.

1:04:52
SINTER STORE. Now you can store the intersection and find differences too SINTER STORE and SDIFF STORE. You can also find and store the difference. So SDIFF STORE and here you give the destination. Let me write final_results_two. And results_two and results_one. So what's different between the two. You'll find and store it.

1:05:08
So this is some of the things I showed you about SET. Otherwise there's a lot more. Besides that, which I showed you. Like SADD I showed SCARD I showed.

Sorted Set Data type Commands

1:05:15
SDIFF I showed SDIFF STORE also. You can extract. You can store the difference. SINTER I told you. SINTER STORE. SUNION. SUNION STORE. SMEMBERS I told. SISMEMBER I told you.

1:05:24
If member belongs to a set. SMOVE. You can move. If you want to move a member from one set to another. So this is there. SMOVE. SPOP there is. And there are many more here. So go see all the REDIS commands. And after SMEMBERS, we come to the sorted sets.

1:05:31
So SORTED SETS. Here click and in this there are many commands. Out of these, I'm going to tell you some now. Like ZADD I'll tell. ZRANGE I'll tell. ZREVRANGE will be there. ZSCORE and ZCARD...

1:05:44
So here let me click and show you. What does ZADD do?

1:05:51
Let me wait and show you how to use it. Here on this. You'll see ZADD here. Click me and see. Here's ZADD. So the syntax here is quite long. Read this theory once. Because this is somewhat complicated in syntax.

1:05:58
The syntax here is like ZADD, you write. Then here you need to write. Then AN... X GT. This and all look. Score then then member. Then score then member. Then score then member. Then score then member. Like this. You can write it.

1:06:07
In this adds all the specified members with the specified score to the sorted set sorted at the key. Creates the key if it does not exist. It adds all the specified members with the specified score to the sorted set sorted at the key. It is possible to specify multiple score member pairs.

1:06:23
Multiple you can do score member. Like I told you. If a specified member is already a member of the sorted set, the score is updated and the element reinserted at the right position.

1:06:30
To ensure correct ordering. If it already exists then the score you give will be updated. And reinsert it at the right position. If key does not exist, a new sorted set with specified members as sole member is created. If the key exists but doesn't hold a sorted set and an error is returned.

1:06:37
So if it doesn't exist then create new. If it exists but doesn't hold a sorted set, an error occurs. The sort score value should be the string representation of a double precision floating point number value.

1:06:44
So +inf and -inf are valid values as well. So this is all. Now float point number it should have. String representation of it should be.

1:07:22
OK so I'll wait. So what else is here? ZADD supports a list of options specified after the name of the key and before the first score argument.

1:07:34
So all options after key name and before score. Here you'll see XX which means. Only update elements that already exist. Don't add new elements. This is for you. XX is there. Then nx which is. Only add new elements don't update already existing elements.

1:07:53
LT only update existing element if the new score is less than the current score. This flag doesn't prevent adding new elements. GKT only update existing element if the new score is greater than the current score. This flag doesn't prevent adding new elements. You read this. You get good information.

1:08:05
And you'll find some good things to work with. Where is this sorted set? When does this data structure work well? Where are these used like scoreboard when cricket matches are... Then you'll have scoreboard. That's automated up and down by score. So then you can use ZADD...

1:08:18
Or like if player's rewards points are ranked by. In some app if a player goes up and down by score, then you can use sorted set. Or if anywhere you need to define...

1:08:31
Where you need to define score rank. So you can use ZADD the sorted set.

1:08:36
OK so read this. You see sorted sets. LRANGE was sorted by score in an ascending way. So this increases. Order. The same element only exists a single time. No repeated elements are permitted.

1:08:49
The score can be modified both by ZADD that will update the element score and as a side effect its position on the set and ZINC by. So you can increase the score. Update. Its order. Will also change.

1:08:59
And this is ascending order like written here. The current score of element can be retrieved using ZSCORE command. And score from that...

1:09:05
So you can retrieve with ZSCORE. And elements with the same score while the same element can't be repeated in a sorted set since every element is unique.

1:09:17
It is possible to add multiple different elements having the same score. That means one score can have multiple different elements. Multiple elements can have the same score. That's explained here. When multiple elements having the same score they are ordered lexicographically...

1:09:28
They're still ordered. The core as first key how...

1:09:44
How are elements with the same score ordered? All members of a sorted set that have identical scores are sorted...

1:10:00
Now let's move to practical commands. Let me first FLUSH all the previous content if there's anything. FLUSH all. It's gone. Now let me clear here. And create one set. ZADD let me do this.

1:10:08
So let me write ZADD. Then here the key. I'll write run. So run is the key. And score-member pairs. Like 100. Then "Virat". Like this I've written.

1:10:23
So let me press enter. This will become one. ZSCORE ZADD I've done. So let me create a set here. Let me create a set. ZADD run 100 Virat. I've written. So this is one member, one score.

1:10:31
And look, let me create the set. Write ZADD and the key is run. And in it I give scores. Let me give 200 then "Sachin". Then 300 "Sehwag". Then I give 150 "Dhoni". And "Rohit". And press enter.

1:10:46
Three integer here has been generated. Now let me look. Zrange do it. Press enter. And get score.

1:10:52
Do this and with scores. So you see here. Virat 100 Dhoni 150 Sachin 200 and Sehwag 300. We inserted this. Sachin we gave 200. Then Sehwag we gave 300. And Dhoni we gave 150.

1:10:59
But this maintains its order. Sorts it. So what was less is above. Increases in ascending order. Then less then more then more then more that way.

1:11:05
Like now let me insert one more. ZADD run 5 score. And I gave it. And "Suryakumar Yadav" is his name na. So I gave 5. So this became the least. So this will come first.

1:11:24
First then 100 then 150 like this. So ZRANGE let me see. Look at the top is now Surya's 5.

1:11:38
So this is how it auto-sorts. So now let me give one more value here. This is 500. I give "Virat". Oh wait, "Virat" is already there.

1:11:51
No, let me give "Virat" No wait. Let me give "Surya". Oh wait, I just gave Surya. Let me give another name. "Vihari". Let me give "Vihari". Let me give "Vihari".

1:12:00
And give him 500. And 500 is a lot, so it'll be at the bottom. Let me see this one too. So it's least first then more then more then more then more then more like this is in ascending order.

1:12:06
Now you can do ZCARD and the key. So ZCARD run and it'll tell you. Six. Number of members. Total we have six members in this. You can count too. One two three four five and six.

1:12:22
So ZCARD and key. So it'll get you. How many members there are in the sorted set in it. So ZCOUNT and key. Let's count. And minimum. Let's say 150. And maximum 300.

1:12:31
So minimum from 150 to 300 maximum. So all scores in this range. Three. Number. So ZCOUNT returns this. How many members made runs in this range.

1:12:40
Meaning who's whose score is in this range. Like Dhoni made 150. Sachin made 200. Sehwag made 300. So three members.

1:12:45
So it's very good. Like if we want to display in a cricket scoreboard...

1:12:51
So just from HERE you can extract. You don't need to write SQL or anything. That's why Redis becomes so popular. And gave us such good structure. So now let me show you one more.

1:13:00
If I want to fetch data based on score, then ZRANGE BY SCORE. I've written this. This key. And score. Then run. And minimum. Let's say 150. And maximum 300. What difference finds. Then it'll show me the members who made runs from 150 to 300.

1:13:08
That'll show me Dhoni, Sachin, Sehwag. If you want scores too, then write here. With scores then it'll show you scores too.

1:13:16
1:13:16
150 and 300 then Dhoni 150 Sachin 200 Sehwag 300. So it shows you members like that. So this is done. Let me clear it.

1:13:23
And let's do one more. If I want to know the rank. If I want to know what's the score. If you want to know any member's score, then ZSCORE and key. Let me run.

1:13:31
And the member? Let me say Virat. And press enter. Virat's 100.

1:13:36
So like if I want to know Surya's, then Surya's is 5. So that's how you'll find it.

1:13:41
Now if you want to know what's the index number of a member, then ZRANK and key. Run and...

1:13:46
Now the member is what? Like Sehwag's. Let me press enter. And what's Sehwag's index? Four. So it's 0 1 2 3 4 5. So Sehwag's is... Wait.

1:13:53
So he's at index 4. And like if I do Vihar, then Vihar is at index 5. So that's how you can use ZRANK to find its index number. OK so I can now show you this. If I want to delete, then ZREM.

1:14:08
So from this key, I want to remove a member. Let's say Surya.

1:14:13
Because he has 5 score which is wrong. Let me press enter. And it'll be removed. Let me look at the ranges again. It's not there now.

1:14:20
So that's how ZRANGE works. It's going well. So you have ZADD ZCARD ZCOUNT ZRANGE by score. And looking at the examples earlier...

1:14:27
You have sorted sets. OK, now let me show you. Let me do ZREVRANGE by score.

1:14:33
ZREVRANGE. So basically descending. Reverse sort. From highest to lowest...

1:14:39
ZREVRANGE. And here you look. ZREVRANGE by score. Then key. And maximum. And minimum. So here's what you need to do.

1:14:44
Maximum becomes 300. And minimum becomes 150. So inverse. Because reverse. And press enter.

1:14:50
So the order is reversed. So highest first. Then less then less. Like this it'll be in descending order. And you'll get. Sehwag 300 Sachin 200 Dhoni 150. Like this you get. The other stuff I can't show because...

1:14:59
There's a lot more commands. But some basics I've shown. With ZADD ZCARD ZCOUNT. ZRANGE. I showed. So ZREVRANGE. SINTER STORE. ZUNION and ZINTER...

1:15:07
You can do a lot with sorted sets. And beyond that everything else is there. ZREM I showed. ZD IFF you can see. ZDIFF STORE. ZCOUNT. ZINC INCREMENT you can do. Intersection you can find. And look ZINTER and ZUNION.

Hash Data type Commands

1:15:24
So that's what I have. The next we have is HASHES here. So this is here. HSET, HMSET and all that are commands in this. Hmm. So what's the difference here? Let me look at HSET first. And then...

1:15:31
How do we use it? First let me look at HSET here? Or HMSET here also you can see.

1:15:38
First let me see HSET. Create and modify. What does it do? It creates and sets the field to its respective value in the hash. Stored at the key. This command overwrites the value of a specified field that already exists in the hash. If the key doesn't exist, a new key holding a hash is created. This command is deprecated.

1:15:55
And its value is written. OK so HMSET is deprecated. It has been replaced by HSET. Which is multiple field. Multiple field value pairs. Can be inserted.

1:16:08
So this HMSET doesn't exist now. That's the older one. So we won't see this. OK so it's done. What if we delete from here? And after it. HGET can get. Get this value. So you specify. Then field. You'll return its value.

1:16:21
You specify and then look. HGETALL in it. So you can get. Get all this. And you can see everything. If you want to check if this specified field exists. Then HEXISTS you can check. Determine whether a field exists. If the field exists or not. HLEN and here you'll set multiple. Field value.

1:16:35
Then there's a lot more. HMGET you can see. HKEYS, HVALS. HSCAN. HSTRLEN. HDEL to delete. Many more commands. There are many more. There's HINCRBY.

1:16:42
Much information. Here I can see. It's object related work so this hash is the best data type. I can see now HMGET.

1:17:06
Let me show HMGET one more thing. Like if I do HMGET. Then I'll write. HMGET run. But HMSET... What is it? So let me show you with HSET and HGET ALL.

1:17:20
Let me do this once more. Let me reset. FLUSH all. Let me do HSET.

1:17:50
HSET and here key is "user_one". And field value pair. So here I give name. Name's value is "Suhani".

1:17:56
Then class. Class's value is 9. Then role. Role's value is 101. And state. State's value is "Raj".

1:18:04
And press enter. You'll see four. Our field value set is done. One you'll get. Only one set.

1:18:15
But you can also set multiple. Let me show. Here let me write the user_two and field name. Name's value is Raj. Class is 9. Role is 102. Here's Judges.

1:18:22
Let me press enter and it's done with four.

1:18:28
Now we need to look. If we HGETALL do it, then user_one if I do it, then all I get.

1:18:34
And if I do user_two, then you get user_two's. So if I do HGETALL on one, then here I'll see field value, field value, field value, field value. Like this.

1:18:40
And if I do HGET and I give user_one, which field's value do I want? Name. So press enter. I'll get Suhani. Only.

1:18:46
But if I do HGET user_two, name, then you get Raj. So like this you can see...

1:18:52
If I want to check if this specific field exists. Then I use HEXISTS and key. User_one and which field I'm checking.

1:19:00
Like let's say name exists or not. If it exists, then one comes. If it doesn't exist like if I give subject. Subject doesn't exist here. So zero comes.

1:19:06
Now if I want to check again that user_one name. Suhani has this now. OK so I've set everything. Let me look again...

1:19:13
OK if you want to delete any field, then you can use HDEL. Here key. User_one and which field. Do you want to delete? Let's delete subject. Subject, enter. It's deleted.

1:19:20
Now if you check HGETALL. You won't get subject. Now here if you want the keys only. Specified data only the fields only or only values.

1:19:26
Then there's also HKEYS. This writes the key. User_one and the fields. You only get. Like this.

1:19:33
Similarly HVALS. Here you give the key. User_one. So only values you get. So this you can also check. If you want to know. Number of fields. So that's also there. HLEN. Let me write it here. And key. User_one. This will tell you how many fields.

1:19:45
So we have four fields.

1:19:52
One, two three four, these four. These four and four you get. So HLEN here.

1:19:58
Besides that if you get specific fields' values. If you know the value. So you can use HMGET. This writes the key. User_one. Which fields' value do you want? Like I want name's value. And I want state's value. Two I've written.

1:20:08
Press enter and two values. You get. So this is also good. If you want to delete all, you can see.

1:20:14
Let me clear this. Let me FLUSH all. So everything goes away. Now one more thing. HMGET. You HMGET. If you want, you can find. If you want, you can remove it. If you want, you can find. If you want, you can get. And it's also good. HGETALL.

1:20:30
There's HINCR. HINC BY. Increment by. This you look. INCR by float. This you see here. Then HSCAN. You see HSCAN. Is also good. This one I'd like to show. So here I'll show you. HSCAN. Let's scan and iterate.

1:20:42
HSCAN what is this? Here I see HSCAN here. What does HSCAN do? It says scan for H. HSCAN, what is this? SCAN here doesn't tell. HSCAN...

1:20:48
You need to write key. Then cursor. From here scan. So you'll see here that it tells. It says. Scan command and the related command HSCAN, SSCAN, and ZSCAN are used in order to incrementally iterate over a collection of elements.

1:20:56
This will scan and iterate. Basically iterate and show you. Like look, SCAN zero. It sets the cursor at zero. From there start scanning. And it tells where it ends.

1:21:02
Where will the next scan be? Next scan is from 17. So you start from 17. So all these elements you can see. So this is how it works. Otherwise read about scan. You'll understand well about how scan works.

1:21:14
This is also pretty useful sometimes. So you should definitely see this once. I'd say see all the commands from here.

1:21:20
Let me come here and show you HSCAN.

1:21:26
So look, here LINDEX is there. LINSERT is there. LLEN is there. And LMOVE is there. And many more things. I've shown you so much. A lot of times it'll be shown, so what I told you now...

1:21:38
The data types you can do with the commands you can do with the commands. OK so that's enough. But go and see all the other REDIS commands from the documentation itself. And I'll tell you in some upcoming videos. For instance how Pub Sub works. I mean how do subscribers publish. How does it work? And how to make data persistent. In how many ways can you make it. Like snapshot technique. And AOF. Append only file. That's also there. How can I create both combining both? And how to create a replica in it.

1:29:01
Like replica. Master-slave concept. What is it? That also I'll tell you. But for now it's not. In some upcoming videos. So you'll get a playlist. And the playlist you'll see in the description of this video.

1:29:13
Now we've seen commands, etc. And basic things. And you can work with Redis. And do great work. But some other features that are there commands beyond. Like features. Like Pub Sub. Or how to make persistent. Or how to create a replica. Master-slave concept. What is it? I'll tell you separately.

1:29:30
Friends if you've seen this much, then don't forget to subscribe to the channel. And definitely come and read the Redis documentation. Thank you very much for watching this video.

---

## Scenario-Based Questions

1. **You need a flag that says "has this user already claimed today's bonus?" and it must auto-clear at midnight. Which command combination do you use?**
   `SET` the key when the bonus is claimed, then `EXPIRE` it with the number of seconds until midnight (or use `SETEX`/`SET ... EX`). Checking `EXISTS` before granting the bonus tells you whether it has already been claimed.

2. **Multiple app servers might try to acquire the same lock at the same time. Which Redis command prevents two servers from both believing they hold the lock?**
   `SET key value NX` (or the standalone `SETNX`). It only sets the value if the key does not already exist, so only the first caller succeeds; the rest get a "not set" response and must retry or back off.

3. **You need a "recently viewed products" list per user, always showing the 5 most recent, most-recent first.** Which data type and commands fit, and how do you cap it at 5 items?**
   A Redis List. Push each new product ID with `LPUSH`, then trim the list with `LTRIM key 0 4` after every push so it never grows past 5 entries.

4. **You want a running visit counter for a page that many concurrent requests update at once. Why is `INCR` safer than `GET` + add-one + `SET` from the application?**
   `INCR` is atomic inside Redis; two concurrent `INCR` calls are serialized by the server and never lose an update. A manual get-then-set in application code has a race window where two requests can read the same value and both write back the same incremented result, losing one increment.

5. **You need to store a signup coupon code so it can never be redeemed twice by different users. Which data type guarantees this, and why?**
   A Set. `SADD` silently ignores a value that is already a member, so attempting to add a duplicate coupon code does not create a second entry, and `SISMEMBER` lets you check redemption before granting the coupon.

6. **A leaderboard must show players ranked by score and support "give me everyone between 150 and 300 points."** Which data type fits, and which command answers the range query?**
   A Sorted Set (`ZADD` to insert score/member pairs). `ZRANGEBYSCORE key 150 300` (or `ZCOUNT` for just the count) answers the range query directly, sorted automatically by score.

7. **You are modeling a student record with name, class, and role fields, and you want to update just one field without touching the others.** Which data type and command do this cleanly?**
   A Hash. `HSET key field value` updates a single field in place; `HGETALL` retrieves the whole object, and `HDEL` removes one field without deleting the rest.

8. **A key holding a token must be retrieved and deleted in one atomic step so no other process can read it after you have consumed it.** Which command does both?**
   `GETDEL key`. It returns the current value and deletes the key in a single atomic operation, avoiding a race between a separate `GET` and `DEL`.

9. **You installed Redis via `snap` and later need to edit `redis.conf` to change persistence settings, but you cannot find or modify the file directly. What is the underlying limitation, and what is the alternative?**
   Snap-based installs sandbox the configuration and do not expose direct file-system control over `redis.conf`; you are limited to whatever the snap package exposes. If you need full configuration control, install Redis via `apt`/source or run it in Docker where the config file is directly accessible.

10. **A new engineer names cache keys like `10001` and `abc`. Why is this a problem, and what naming convention should replace it?**
    Such keys are not descriptive; nobody can tell what the key represents or which entity/domain owns it. The convention is `entity:id:field` style, e.g., `user:1000:followers`, which stays readable and groups related keys logically.

11. **You want to know how many students are enrolled in a class and quickly check if a class already has a member named "Rahul," without fetching the whole set.** Which two Set commands do this?**
    `SCARD key` returns the member count, and `SISMEMBER key member` checks membership directly, both without pulling the full set into the application.

12. **Two departments each maintain a Set of customer IDs, and you need the customers common to both promotions, plus the customers unique to campaign A.** Which Set operations answer each question?**
    `SINTER setA setB` returns the customers common to both. `SDIFF setA setB` returns the customers only in `setA` (present in A but not B).
