from random import sample
from joshlib.ollama import OllamaClient

from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "mistralai/Mistral-Nemo-Instruct-2407")

tone = """
The preacher delivers this sermon in a passionate, urgent, and contemplative tone, emphasizing God's presence and promises of salvation to broken and sinful individuals, inviting listeners to respond in faith by stepping onto the ladder of Jesus Christ.
"""
thesis = """
God's presence is the greatest blessing He can offer to humanity, and it is only through faith in Jesus Christ that we can experience this presence, which bridges the gap between a holy God and broken, sinful humanity.
"""
summary = """
The sermon, titled \"When God Meets Us in Our Mess, Part Two,\" recounts Jacob's flight from Esau after his deception, emphasizing the consequences of his actions and God's allowance for individuals to experience the results of their sin as a path to repentance. In his desperate state, Jacob dreams of a ladder connecting heaven and earth, where God appears to him, reiterating the Abrahamic covenant and promising His unfailing presence. This encounter leads to Jacob's vow of faith, signifying a turning point. The sermon then interprets Jacob's ladder dream through John 1, where Jesus declares Himself to be the fulfillment of this vision, the sole bridge and mediator connecting a holy God and sinful humanity. The concluding application underscores that God meets broken individuals in their struggles, offering His presence and promises through Jesus Christ.
"""
outline = """
I. Introduction\n    A. Brief welcome and introduction\n    B. Introduction to Genesis 27-28\n\nII. The Journey to Brokenness\n    A. Jacob's deception and sin\n        1. Deceived his father, Isac\n        2. Lied to his blind father to steal the blessing\n    B. Consequences of sin\n        1. Rebekah's scheming and plotting\n        2. Jacob's exile and 20-year absence from home\n\nIII. God's Presence in Brokenness\n    A. Jacob's dream and encounter with God\n        1. The ladder connecting heaven and earth\n        2. Angels ascending and descending on the ladder\n    B. God's promise to Jacob\n        1. Land, descendants, and blessings for his family\n        2. Presence of God in his life\n\nIV. Jesus as the Bridge (John 1:43)\n    A. Jesus' calling of Philip and Nathanael\n        1. Nathanael's skepticism and Jesus' response\n    B. Jesus as the ladder between God and humanity\n        1. One way to heaven, one mediator between God and man\n\nV. Application\n    A. God meets broken people where they are\n        1. No need for us to clean up ourselves before receiving God's presence\n    B. God gives his presence and promises\n        1. Exceedingly great and precious promises of forgiveness and justification\n        2. Presence of God in believers' lives\n\nVI. Invitation\n    A. Response in faith to the gospel message\n        1. Recognizing the ladder has come down from heaven\n        2. Stepping on the ladder by faith
"""

og_transcript = """
Oh, you're good.
All right.
Well, thank you guys for leading us in worship this morning.
All right, guys.
Did y'all enjoy the Brunner family?
Yeah, I did as well.
Yeah, it's always a blessing to have you guys with us.
See, this morning, let's look in the book of Genesis, chapter 27.
We will pick up where we left off.
Oh, yeah, Dismissed for Children's Church.
Almost forgot.
See, I called it.
I redeemed myself.
Dismissed for Children's Church.
There we go.
I got it.
Promise this ain't my first day, right?
All right, Genesis 27.
We're going to be picking up in verse 47.
And we're going to be looking through chapter 28 this morning.
And if you remember, this is part two of When God Meets Us in Our Mess, part two.
And this is when God meets Jacob at his lowest point in his life so far.
Let's pick up here in verse 41 of Genesis 27.
The Bible says,
So Esau hated Jacob because of the blessing with which his father blessed him.
And Esau said in his heart,
In the words of Esau, her older son were told to Rebekah.
So she sent and called Jacob, her younger son, and said to him,
Surely your brother Esau comforts himself concerning you by intending to kill you.
Now, therefore, my son, obey my voice.
Arise.
Flee to my brother Laban in Haran and stay with him a few days until your brother's fury turns away,
until your brother's anger turns away from you and he forgets what you have done to him.
Then I will send and bring you from there.
Why should I be bereaved also of you both in one day?
And, of course, Rebekah says to Isaac,
I'm weary of my life because of the daughters of Heth.
If Jacob takes a wife of the daughters of Heth like these who are the daughters of the land,
what good will my life be to me?
And then Isaac called Jacob and blessed him and charged him and said to him,
You shall not take a wife from the daughters of Canaan.
Arise, go to Paddan Aram to the house of Bethuel, your mother's father,
and take yourself a wife from there of the daughters of Laban, your mother's brother.
And may God Almighty bless you and make you fruitful and multiply you,
that you may be an assembly of peoples and give you the blessings,
and give you the blessings, and give you the blessings,
and give you the blessing of Abraham to you and your descendants with you,
that you may inherit the land in which you are a stranger, which God gave to Abraham.
So Isaac sent Jacob away, and he went to Paddan Aram, to Laban, the son of Bethuel,
the Syrian, the brother of Rebekah, the mother of Jacob and Esau.
Let's go to the Lord in prayer.
Father, we thank you for your word.
Lord, we thank you that it is relevant to us today.
Lord, we thank you that it is relevant to us today.
Lord, it is inspired, it is inerrant, it is sufficient for faith and practice.
Lord, we pray that you would open our eyes to see wonderful things from your law.
Lord, may your ears be open, may your hearts be receptive.
Father, we pray that we would see your glory in the gospel,
as the gospel is presented even here in Genesis.
Lord, we pray that your name would be hallowed.
Lord, that your kingdom would come.
Lord, that your will would be done on this earth, in this church, in our lives, Lord.
Let us live our lives under the crown of King Jesus.
Lord, we pray if anyone's lost this morning,
Lord, that the gospel would become so sweet, so irresistible to them, Lord.
Lord, you would break the hardened heart.
You would comfort the broken heart, Lord.
That those who are idle would be warned,
and those who are without strength,
would be encouraged.
Lord, edify your people.
Lord, beautify your bride.
Through the washing of the water of the word, we pray.
Lord, speak through me.
Jesus, be big this morning.
In Jesus' name, amen.
All right, guys.
When God meets us in our mess, part two.
Now, if you remember from last week,
we looked at one of the most dysfunctional families in all of Scripture, right?
Right?
Do you remember some of the elements of dysfunction?
You guys remember?
We saw favoritism.
We saw deception.
We saw false repentance.
We saw brotherly hatred.
And then we saw a murder plot, right?
We saw Isaac favoring Esau and Rebekah favoring Jacob.
We noticed that Jacob was every bit the deceiver his mother was.
We watched him lie to his blind father by disguising himself
as his older brother to steal the blessing.
And then we saw Esau's tears, not of godly sorrow,
but of regret over losing what he had once despised.
And it was messy, right?
But we had to deal with the depths of family dysfunction.
And then we ended with this truth.
We talked about how God's sovereign purposes are never thwarted by our sin.
And how that God chooses Jacob to carry on the covenant line,
not because Jacob deserves it,
but because God is faithful to his promises.
And then we talked about how sin is the ultimate dysfunction.
Sin causes disruption in harmony between us and God
and between us and one another.
And it's only through the gospel that that harmony,
that fellowship is restored.
And the good news is we will one day see reconciliation take place.
Oh, but not yet.
Not yet.
We have many, many years until we see that.
In fact, we're going to see 20 years take place in Jacob's life
before he is one day reconciled to his brother Esau.
But you didn't see that coming.
But I get ahead of myself, right?
For now, we see that Jacob has the blessing.
But he's lost everything else.
He flees for his life from a brother who wants him dead.
He leaves his parents.
He leaves his home.
He leaves everything comfortable, everything familiar.
And we'll see that God takes him on a journey to break him
and then to rebuild him into the man God has called him to be.
So this morning, you may be asking,
is there any hope for me?
Can God meet me in the midst of my own brokenness and despair?
Can God help me deal with the consequences of my own sinful actions?
Because that's exactly what Jacob is dealing with this morning.
This is partly his fault.
But yet, we see that God is going to meet him in his lowest point.
So this morning, if you feel broken and desperate and alone,
if you're wondering, has God given up on me?
Can God meet me where I am?
Well, there's good news for you this morning.
So let's first look at the journey to brokenness.
So we read here in chapter 28,
Isaac blesses Jacob properly this time,
and then he sends him away.
But once again, we see Rebekah eavesdropping, right?
She has sharp ears.
She's not only a good cook.
She can hear everything.
And she overhears Esau's promise to kill Jacob.
And so Jacob is sent off by his mom and dad to his mother's family in Paddan Aram.
And he's to stay there until Esau.
And Esau's anger subsides.
And from there, Jacob is also to find a wife from among his mother's people.
Now, Rebekah thinks she's helping Jacob get ahead, right?
I'm going to help you steal the blessing, my favorite, beloved son.
Little does she know that through her scheming and plotting,
she is sending her son away.
And he will be away for 20 years.
She will die.
She will never see her son again.
She lost two sons that day.
She lost the relationship with her son Esau.
He would move to the mountains of Seir.
And then she would send off her beloved son Jacob.
She would never see his face again.
Friends, that's the far-reaching consequences of sin, isn't it?
You know, as the old-time preachers say,
it takes us farther than we want to go.
It keeps us longer than we want to stay.
That's exactly what happened with Jacob and Rebekah.
And friends, we will never get ahead in life
by living life contrary to God's design.
Never.
Now, Jacob, he has the blessing, but he's leaving everything behind.
He's fleeing his brother's murderous rage.
He's leaving his mom who loves him so much.
He's heading to an unknown land.
Now, he should think, yes, I've won.
I've got what I've always wanted.
I've got the birthright, and I've got the blessing.
Oh, but Jacob never felt more like a loser in his life.
But here's what God is doing.
He's leading Jacob to the place where he will learn his lesson
because ultimately, as we'll see in the coming weeks,
Jacob is going to Laban, Rebekah's brother, be his uncle.
And he's going to serve 14 years for two wives.
And then he's going to serve another six years.
And he's going to have his wages changed ten times.
Jacob is going to reap what he sowed.
Jacob is a deceiver.
Oh, he's going to an even bigger deceiver.
He's going to meet an even bigger manipulator than himself.
Galatians 6 says, don't be deceived.
God is not mocked.
Whatever a man sows, that will he also reap.
God is allowing Jacob to reap the consequences of his own actions.
He deceived his father.
So he will be deceived multiple times by his father-in-law.
And get this.
Here's a cool little tidbit that stood out to me.
Remember, how did he deceive his father?
Anybody remember?
By goat skins, right?
By goat skins.
Well, years and years later, when Jacob is a father himself,
Jacob's own sons will use the blood of a goat
and put it on clothing.
His favorite son's clothes, and deceive him and say, Joseph is dead.
So we have a deception by goats and deception by clothing.
Jacob reaps exactly what he sowed.
But you know, sometimes that's the most loving thing God can do for us,
is let us reap the consequences of our own sin.
But not to destroy us, but to break us and to bring us to repentance.
So that we might turn from these self-destructive ways.
And we might find hope and healing in the gospel.
And that's the beautiful thing.
God doesn't just let us reap what we've sown to totally destroy us,
but to break us, humble us, and remake us.
And now we find Jacob at his lowest point.
Look in verse 10.
And now Jacob went out from Beersheba and went toward Haran.
So he came to a certain place.
Stayed there all night because the sun had set.
And he took one of the stones of that place and put it at his head.
And he laid down in that place to sleep.
He must have been tired.
That's all I can say.
I remember reading this as a kid.
And I used to think, this is like one of the coolest stories ever.
He gets to sleep outside all night.
Now that I'm old, it's like, nah, I couldn't be comfortable, right?
But he lays down.
And then he begins to dream.
And behold, a ladder was set up on the earth and its top reached to the heaven.
And there the angels of God were ascending and descending on it.
What a strange dream.
Let's pause right there.
Let's think about Jacob now.
Here's his mommy's favorite son.
He's the soft, smooth man of the garden.
Now he's a fugitive in the wilderness.
This is a dream.
This is his brother's territory.
This is where hunters go.
This ain't where gardeners go.
He's on a 500-mile journey to Paddan Aram.
He's approximately 50 miles in, possibly the second night.
And he comes to a certain place.
And we'll later know that that place is called Luz.
Luz simply means almond tree.
Little does he know that his grandfather, Abraham, has been to this place.
Before years and years ago and actually set up an altar here.
It will later be known as Bethel.
Jacob, he don't really seem to mention that.
Maybe he doesn't even know.
Little does he know God is going to meet him here at his most lowest and most desperate time, though.
He's exhausted.
He takes a stone.
He pits it under his head as a pillow.
And he goes to sleep.
Now picture this.
He's alone.
He doesn't.
He doesn't have the love of his mother to comfort him.
He has the hatred of a brother who wants him dead.
He has the disgrace of a deceived father.
Back home, he had riches, food, anything he wants.
Now, he only has what he can carry.
He's messed up.
He's exhausted.
He's desperate.
He's a man who's stolen covenant promises.
And yet, he has absolutely nothing to show for it.
Nothing.
At all.
He's a fugitive.
He has the heavens for his canopy.
He has the stars as his only source of light.
He lies on the dark, cold, damp ground.
No doubt, he's thinking, Lord, how on earth did I get here?
Why did I do this?
He's using a stone for a pillow.
I like to say he's between a rock and a hard place.
Literally and figuratively, right?
He has everything stripped away.
He has no impressive spiritual resume.
He's a lying, manipulating deceiver.
And no doubt, he's just lying there on his back.
And he's looking up at the stars.
And he's probably heard his dad talk about God's promise to his grandfather,
how he's going to have descendants as many as the stars in the sky.
And he's like, boy, that's coming true, ain't it?
I have absolutely nothing.
What have I done?
And that, right then, is when God shows up.
Maybe you have some of those moments in your own life.
When you're flat on your back and you're like, Lord, how did I end up here?
What have I done?
That is when God shows up, isn't it?
Now we look.
In verse 10 through 15, God appears to him in a dream.
Verse 12, he dreams a dream.
And there's the ladder.
And it's connecting heaven and earth.
And angels are ascending and descending upon it.
Now, what on earth is this?
What is this ladder?
More literally, in the Hebrew, it means a stairway.
A stairway, specifically, that connects heaven and earth.
And the Hebrew word for stairway, sulam.
And it's the only time it's used in the entire Bible, by the way.
The entire Old Testament.
The King James translates it as ladder.
That's a pretty good definition.
Another definition could be stairway.
In other words, this is a bridge, right?
It bridges heaven and earth.
It bridges the gulf between a holy God and a desperate, sinful man.
And then the angels are ascending and descending on this ladder.
So, what does that mean?
It means God is saying, Jacob, I'm still with you.
My angels are here to protect you.
I'm giving you my presence and I'm giving you my promises.
I know you don't deserve it.
You scoundrel, as me and Josh like to say.
You don't deserve any of this.
But yet, I am still with you.
Even at your lowest point, I'm with you.
Now, I like to think of this vision as the opposite of the Tower of Babel in chapter 11.
Remember, they build this huge tower, this ziggurat.
That, kind of like a pyramid, that reaches the heavens so that they may commune with the gods.
Jacob has no such ability.
Didn't really work in chapter 11 either, did it?
But we notice that when Jacob cannot make his way to God, what does God do?
God makes his way to him.
He can't go up, so God must come down.
In verse 13.
Behold, the Lord stood above it, and the Lord says, I am the Lord, Yahweh.
That's his covenant name.
I am the God of Abraham, your father, and the God of Isaac.
Now, I've learned this.
This is cool.
You guys ready for something really cool?
It says, the Lord stood above it.
In Hebrew, it can also mean the Lord stood beside it.
In other words, God was at Jacob.
At Jacob's side, as he is lying on the ground, sleeping on a pillow, God is beside him.
God is with him.
God has come to earth, as it were.
How awesome is that?
Some of you are starting to make connections.
Some of you see where this is going.
I love it.
Man, I love it.
When he can't reach God, God comes down to him and reveals himself as the covenant-keeping,
promise-keeping God.
God begins to bless him.
He says, the land on which you lie, I will give to you and to your offspring.
Your offspring will be like the dust of the earth, and you shall spread abroad to the
west and to the east and north and south, all directions.
And in you, your offspring, shall all the families of the earth be blessed.
And then he says, behold, I am with you, and I will keep you wherever you go, and I will
bring you back to this land, for I will not leave you until I have done what you have
done, what I have promised.
Praise God.
Is that not beautiful?
By now, you guys should be remembering this passage.
This is the Abrahamic covenant, and God has reiterated it time and time again to Abraham
and to Isaac, and now he gives the same covenant blessings to Jacob.
That is, a people, a place, and a promise, right?
I'm going to give you land, descendants, and then you, all the families of the earth,
will be blessed.
That's the promises, but the most precious thing that God gives is his presence.
He says, I am with you, very close to the writer of Hebrews when he says that he will
never leave us or forsake us, right?
That he's with us.
See, all Jacob's life, he's been struggling, striving for blessings, and God right here
is saying, Jacob, I've already blessed you because I'm good, not because you deserve
it, but because I am faithful to my promises, the promises I made to your father and your
grandfather.
You haven't earned it.
You haven't proven yourself.
You haven't demonstrated character or faithfulness at all, but yet I am true to my word because
my promises are contingent, not on your performance, but on my character.
Praise God for a faithful God.
And then he gives him the greatest blessing of all.
That is not his promises, but his presence.
He says, I am with you.
Jacob, all your life, you thought you needed things to be successful.
You thought you needed me.
You thought you needed material blessings and possessions, and you were willing to do
anything to get it.
Jacob, the greatest blessing I can give you is myself.
The greatest blessing anyone can receive is the presence of God with them.
And God is saying, Jacob, I will never leave you.
I will never forsake you.
I will make sure all of my promises come true.
Believer, that is a promise for you as well.
He will finish what he started.
He will never leave you or forsake you, even at your lowest.
Jacob's response in verse 16.
Jacob awoke from his sleep and said,
Surely the Lord, Jehovah, is in this place, and I did not know it.
He thought he was alone.
He thought he was in some random place called Almond Tree.
Must have had almond trees there.
I don't know.
Little did he know, he is in the very presence of God.
He thought he's forfeited God's blessing through his deception.
He thinks, man.
It can't get any worse.
God, surely he's going to abandon me.
I've messed up and I've lost everything.
And God says, oh, no, boy.
I am still with you.
Praise God.
Friends, how many of us have thought, surely God can't be with me now.
I've blown it.
I've messed up too many times.
I'm in this mess I've made.
I'm reaping consequences of my own sinful actions and decisions.
Friends, that is when God shows up, isn't it?
Not just on the mountaintop, but in the valley.
And in fact, I believe that it's in times of brokenness and times of loneliness and times of heartache.
That is the time when God shows up in the strongest and sweetest of ways.
When we are at our worst, that's when God is at his best.
When we are broken, that is oftentimes when we feel his healing touch the most.
When we are betrayed, that is oftentimes when we feel the presence of God and the sweetness of his spirit with us.
God shows up in loves, in the hard, ordinary, broken places.
Friends, he'll find you even when you're sleeping on rocks.
He'll find you even in your darkest hour.
When you have made a mess of your life, friends, God is still there.
And he is reaching out to you with mercy and with grace.
Grace that knows no end.
So hear me this morning.
God's grace is greater than all of your sin.
You will never be able to out-fail or out-sin the grace and mercy of God.
It's impossible.
You will never exhaust his love for you.
You will never exhaust the mercy that God has for sinners.
Praise God for that.
Jacob says, how awesome is this place?
No joke.
Verse 17.
This is none other than the house of God.
This is the gate of heaven.
Verse 18.
He takes the stone he had used as a pillow and he sets it up as a pillar and pours oil on it.
Now, that's not a play on words, okay?
I know some of the old folks say pillar for pillow.
And y'all are sleepy this morning.
Y'all laugh.
That's a joke, okay?
That's a joke.
It wasn't in my notes, I promise, okay?
He makes his pillow into a pillar, okay?
A monument.
A memorial of the presence of God.
He pours oil on it and he names the place Bethel.
Anybody want to take a stab at what Bethel means?
You guys already know this.
House of God.
There we go.
It's God's house.
God is with him.
Abraham, his grandfather, had camped here and built an altar here before.
Years later, the same God is here.
Now, notice.
The place hasn't changed.
The stone hasn't changed.
His circumstances haven't even changed.
But his perspective has changed.
Right?
Now, he's getting his eyes off of his problem.
And he's getting his eyes on the one who can fix his problem.
Right?
He says, now, God is here.
And a place, was, becomes the place.
The house of God.
Isn't that interesting?
When my life becomes his life.
When my mess becomes his message.
When my brokenness and despair becomes a testimony.
That's exactly what God is doing here.
God shows up.
In ordinary, hard, broken places.
Look in verse 20 through 22.
And Jacob made a vow saying,
If God will be with me and keep me in this way that I'm going.
And give me bread to eat and clothing to bid on.
Man.
He knew how to shake somebody down, didn't he?
Here he is doing it with God.
Lord, if you'll keep me safe.
If you'll provide for me.
Give me food.
Give me clothing.
Then, or so that I come back to my father's house in peace.
Then the Lord shall be with me.
I'll be my God.
Now, God had already promised.
I will bring you back.
For 20 years, Jacob could hold on to this promise.
I will go back to the land of Canaan.
But also, fast forward hundreds of years into the future.
The Israelites who are called by this man's name.
When they are in Egypt as slaves.
They will have this verse to hang on to.
That God will bring us back to the land of Canaan.
The land of promise.
Just as he did our forefather, Jacob.
So, there's a near and a far fulfillment in these words.
But he says, Lord, if you keep your word.
If you do exactly what you promised.
Then, the Lord will be my God.
And this stone, which I have set as a pillar, shall be God's house.
And of all that you give me, I will surely give you a tenth.
That is, a tithe.
Now, Jacob's vow isn't perfect.
His faith isn't perfect.
It's kind of transactional, right?
It's an if-then kind of deal.
If you do this, then I'll...
Do that.
But he's a baby believer at this point.
I believe this is where Jacob gets saved.
This is where he places his faith in the God of Israel.
In the God of Isaac.
In the God of Abraham.
He's committing himself to the God who had committed himself to him.
Saying, Lord, if you'll keep your word.
You'll be my God.
Now, he doesn't have everything figured out.
He's as much like us.
He has doubts.
He has questions.
He has imperfect trust.
Friends, God is not looking for you to have all the answers.
He's looking for you to take the measure of faith that he's given you.
Take the oil and pour it out on the rock and say, Lord, I trust you to keep your word.
You're my God.
The Lord saves him.
Well, there's much work to do.
Because God must also subdue him and separate him and sanctify him.
And it's going to take 20 years.
20 years to do this.
But now, Jacob, he's beginning his life with God.
This is a new beginning for him.
The house of God, the gateway to heaven, is the gateway to his new life.
And God, through it all, will be...
He will keep his promises and he will bring him back to the land.
Now, we could end here, and that would be a good story of God keeping his promises, right?
Of God showing grace to broken, undeserved people.
But, oh man, it gets so, so much better.
Where do we see Jesus in this passage?
Because if we don't see Jesus, there is no gospel message.
And I want you to do this.
Will you do?
Will you do this for me?
Turn in your Bibles to the book of John, chapter 1.
John, chapter 1, beginning in verse 43.
I'll tell you what, I've been so excited all week to bring this out.
I'm telling you.
It's like, man, this is awesome.
This may be new info for some of you.
Some of you have probably heard it before.
But, man, it's so good.
John, chapter 1, beginning in verse 43.
I'll give you a second to get there because you all need to track with this.
Now, this is early in Jesus' ministry, by the way.
The Bible says,
The following day, Jesus wanted to go to Galilee,
and he found Philip and said to him,
Follow me.
So, this is the calling of the disciple, Philip.
Now, Philip was from Bethsaida,
the city of Andrew and Peter.
So, Jesus is calling some of his first disciples.
And then, as all good disciples do,
Philip goes and starts telling people about Jesus.
He's a disciple who wants to go and make more disciples.
And he finds his buddy, Nathanael.
And he says to him,
We have found him of whom Moses in the law and also the prophets wrote,
Jesus of Nazareth, the son of Joseph.
Well, Nathanael says,
Can anything good come?
Can anything good come out of Nazareth?
Wow.
Thanks, Nathanael.
Philip says,
Come and see, old boy.
You don't even know.
Come and see.
And Jesus sees Nathanael coming toward him.
Jesus says something interesting.
He says,
Behold an Israelite indeed,
in whom is no deceit.
Underline the word Israelite.
In whom is no deceit.
Circle the word deceit.
Nathanael was astonished.
How do you know me?
And Jesus answered and said to him,
Before Philip even called you,
while you were sitting under the fig tree,
I saw you.
It's like I was there beside you.
Nathanael said to him,
Rabbi, you are the son of God.
You are the king of Israel.
Jesus answered and said to him,
Because I said to you,
I saw you under the fig tree,
do you believe?
You will see much greater things than these.
Oh boy, listen to this.
Most assuredly, I say to you,
Hereafter you shall see heaven open
and the angels of God ascending
and descending on the Son of Man.
Amen.
And three hallelujahs back to back.
Have we not read that somewhere before?
Come on, somebody.
I know it's sleepy and rainy outside,
but come on, somebody.
Who is?
Who is that ladder?
Who is that ladder?
I'm getting ahead of myself.
I've got to calm down here.
Fast forward thousands of years
from where Jacob is here in Genesis.
Okay?
And we see Jesus calling his first disciples.
And he finds this man named Nathanael.
And Nathanael has been sitting under a fig tree.
And by the way,
that was the customary spot for reading the law
and meditating.
He was reading something.
Somewhere in the law of God,
we can only guess which passage of Scripture
he's reading based upon what Jesus tells him.
Right?
I think.
Stab in the dark here.
He's probably reading Genesis 28.
Perhaps he's contemplating,
how can God be with me?
And if he is,
how can I know that he's,
he's with me?
We really don't have a back story on Nathanael
except that he's from the same town as Peter and Andrew.
He's probably a fisherman as well.
But how can I be assured that God's with me
in this backwater town?
And then Philip brings Jesus
and introduces him as Jesus of Nazareth,
the one that the Scriptures have prophesied about.
And he said,
Nazareth?
Anybody,
anything good come out of Nazareth?
And Jesus says,
you are a son of Israel.
Remember?
The name later given to who?
Jacob, right?
The man here in Genesis 28.
You're a son of Israel
in whom is no deceit.
Unlike your father Israel,
you are not a deceiver.
You are not a conniver.
You are not a manipulator.
You are a man looking for truth.
And here he is.
You've been reading about a ladder between heaven and earth.
You're questioning how God,
how God's presence can be with you.
We can only imagine all these thoughts
are running through Nathanael's head.
And then Nathanael asks,
how do you know me?
We've never met.
And Jesus says,
listen,
before Philip even called you,
I saw you under the fig tree.
And by the way,
I know what you were reading.
Why?
Because like God was beside Jacob,
God was with Nathanael.
Jesus was right there with Nathanael.
Nathanael becomes a believer.
He confesses, you are the Christ,
the son of the living God.
You're not just a rabbi or a good teacher or a good man.
You are the Messiah.
And Jesus says, you haven't seen anything yet.
One day you'll see the heavens open
and you'll see the angels of God
ascending and descending on the son of man.
What is Jesus saying?
He's saying, I am the ladder
that Jacob dreamed about.
Remember, this was a vision given to him by God in his dream.
I am that ladder
that connects a holy God in heaven
with sinful man on the earth.
I am the bridge between God and man.
And the angels of God ascend and descend on me.
What does that indicate?
I believe one indicates his heavenly origin.
He's the son of God from heaven.
But also, I believe it pictures his return in glory
when he returns with the angels in power.
So let's talk about this.
How Jesus is the bridge between God and humanity.
Jacob's ladder, his dream, was just a picture.
It was a preview.
It was a promise of something that God would do.
Somehow, someway in the future,
God is going to span this gulf
between himself and broken humanity.
Well, first Timothy 2, 5 says,
there is one God.
And there's one mediator between God and man.
Who is that?
The man Christ Jesus.
The one who is fully God.
In his essence, he is divine.
So he lays a hand on divinity.
And the one who is truly man,
who lives in the body of flesh,
but with no sin nature,
and lives a sinless life.
And he lays his hand on humanity.
And you know what he does?
He brings them together.
He is that ladder.
He is that bridge
that spans the chasm that sin created.
Separating us between a holy God.
The cross is the bridge.
Jesus is that bridge.
He is the go-between.
He is the mediator.
He is the one who reconciles us to God.
Friends, he does what religion cannot do.
So many people are attempting to,
to climb their way to God, right?
They're building their own towers of Babel.
Trying to be good enough.
Trying to clean themselves up.
Trying to clamber up the ladder with all of their might.
And then, their foot slips.
They fall back into sin.
Then they topple all the way down.
It's just exhausting.
You can't make your way up.
But God does for us what we cannot do for him.
When we can't reach him,
he comes down to us, right?
And all of us, we're like Jacob.
We're deceptive, self-serving, unworthy
of nothing but judgment.
There's a gap between us and God
that we can't cross on our own.
But then Jesus comes down.
The Bible tells us in John 1, 14
that the Word became flesh and dwelt among us.
God crossed the gap that we couldn't cross.
And he meets us in our mess.
And in our brokenness.
While we are sleeping on rocks.
While we are in between a rock and a hard place.
And he sends Emmanuel who is God with us.
And he leaves the glories of heaven
to walk the dust of the earth.
To go to the cross.
To be buried and to rise again.
I love what A.W. Pink says.
He says,
Right down where the fugitive lay,
the ladder came.
And right up to God himself the ladder reached.
Praise God.
The cross wedged in the dirt of earth
with Jesus the Son of God
hanging upon it in the expanse.
Bridges the gap between a holy God
and sinful man.
He is the ladder.
He is the way.
Jesus says in John 14, 6
I am the way, the truth, and the life.
And no man comes to the Father but by me.
See, Jesus isn't a way.
He's the way.
He's the ladder in Jacob's dream.
Just as there is but one way to heaven.
Right?
It's only one way.
It's only one ladder.
Only one bridge.
Only one mediator between God and man.
And when we cross this bridge
we cross over from darkness to light.
From death to life.
From condemnation to justification.
From brokenness to healing.
Remember what I said.
Remember what I said.
Remember what Bethel means.
It's the house of God.
And who is Jesus but God with us?
Remember before his birth
it says you are to name him Emmanuel, God with us.
Matthew 1, 23.
Friends, Jesus is the ultimate house of God with us.
He is God's presence.
Come down.
And we as believers, 1 Corinthians 3, 16
says that we are the temple of the Holy Spirit
and God dwells in us.
So we don't have to be like Jacob
and ask, is God in this place?
He is in this place.
If you are a believer, he is in you.
You are Bethel.
You have the presence of God
living in you.
And if you are a believer, you don't have to ask
is God with me?
He is with you.
He will never leave you or forsake you.
Even if you are a broken sinner on the run
like Jacob, guess what?
God is beside you as well.
He is the good shepherd
seeking the lost sheep.
He has not abandoned you to your sin.
He has not left you lost and alone
in the wilderness.
See, Jacob was in a wilderness, wasn't he?
He was like a lost sheep.
But here was God coming to his rescue
as his shepherd
and gave him exceedingly great
and precious promises.
The same thing he does with us as believers.
So as a word of application,
number one,
God meets broken people.
God meets broken, dysfunctional people
where they are.
He doesn't wait for us to clean up ourselves.
To somehow stop doing this
and stop doing that so that we are presentable.
No, he comes to fix us in our
brokenness, right?
Jacob was a mess, a liar, a deceiver,
a manipulator, running for his life.
And maybe you have done all these
things and worse.
And you have been running from God
because you think it can't get any worse.
And you think there is no way God could ever receive me.
Friends, God has already made the way
for you to be forgiven.
For you to be received.
To receive his salvation right now.
You just need to repent of your sins
and place your faith in Christ.
You just need to get on that ladder
and he will take you the rest of the way up.
Secondly, God gives us his presence
and his promises.
Yes, he gives us exceedingly great
and precious promises, eternal promises.
He promises us forgiveness
and justification and a home in heaven.
But the greatest promise
is his presence.
The promise that neither life or death
or angels or rulers or things present
come or powers or height or depth
or anything in all creation.
Nothing will be able to separate you
from the love of God that is in Christ.
God was with Jacob. God will be with you.
Friends, will you respond
in faith?
Will you realize that the ladder has come down
from heaven?
He has reached out to you.
Will you by faith step on this ladder?
The Lord Jesus Christ.
As they come and give us
a song of invitation.
Please take some time
and reflect on the sermon.
Take some time and pray.
And if you would like
someone to come and
pray for you,
pray with you.
I'm up here.
Grab me, grab a friend.
Come to the one
who has come down to you.

"""

prompt = """
You are a Senior Editorial Director specializing in sermon publication.

You are performing a FINAL INTEGRITY AND POLISH PASS on a completed sermon manuscript.

This is not a creative rewrite.
This is not a theological enhancement.
This is not an argument restructuring task.

Your job is to:

Remove:
Any remaining transcription artifacts.
Filler phrases
Accidental repetition
Broken or looping sentences
Incomplete thoughts
AI-induced rhythm glitches
Redundant phrasing that weakens clarity
Smooth awkward wording ONLY where clarity demands it.

Preserve:
The preacher’s voice
The preacher’s tone
The theology
The argument structure
The rhetorical intensity
All Scripture references exactly as written
Maintain spoken-word cadence suitable for sermon publication.

Do NOT:
Add new theological insight
Expand applications
Shorten for efficiency
Modernize language unless it corrects a clear error
Improve transitions unless they are broken
Replace strong language with softer phrasing
Change the thesis
Change the emotional weight

OUTPUT REQUIREMENTS

Return:
Provide the full revised sermon in its entirety.

Extra context:
Sermon Tone: {TONE}
Sermon Summary: {SUMMARY}
Sermon Thesis: {THESIS}
Sermon Outline: {OUTLINE}

SERMON TEXT BEGINS BELOW:
<<<
{TEXT_TO_POLISH}
"""

sermon = """
When God Meets Us in Our Mess, Part Two
15 February, 2026
Thesis: God's presence is the greatest blessing He can offer to humanity, and it is only through faith in Jesus Christ that we can experience this presence, which bridges the gap between a holy God and broken, sinful humanity.
Summary: The sermon, titled "When God Meets Us in Our Mess, Part Two," recounts Jacob's flight from Esau after his deception, emphasizing the consequences of his actions and God's allowance for individuals to experience the results of their sin as a path to repentance. In his desperate state, Jacob dreams of a ladder connecting heaven and earth, where God appears to him, reiterating the Abrahamic covenant and promising His unfailing presence. This encounter leads to Jacob's vow of faith, signifying a turning point. The sermon then interprets Jacob's ladder dream through John 1, where Jesus declares Himself to be the fulfillment of this vision, the sole bridge and mediator connecting a holy God and sinful humanity. The concluding application underscores that God meets broken individuals in their struggles, offering His presence and promises through Jesus Christ.
Sermon
Oh, you are good. Indeed, alright. Well, thank you all for leading us in worship this morning. It's always a blessing to have you with us. See, this morning, let us look into the book of Genesis, chapter 27.
Alright, guys. Did y'all enjoy the worship led by the Bruner family this morning? I sure did, as they brought a powerful reminder of God's presence with us today. It was truly a blessing to have them here, and their ministry serves as a testament to the promises of salvation that God extends to broken and sinful individuals like you and me. Now, let's turn our attention to God's Word this morning, as we look into Genesis, chapter 27.
We shall resume where we left off last week. Now, before we proceed, let me remind you that we dismissed our children for Children's Church today. I apologize if I overlooked mentioning that earlier. Now, turning to Genesis chapter 28 this morning, we'll begin in verse 47.
And if you remember, this is part two of 'When God Meets Us in Our Mess', part two. And this is when God meets Jacob at his lowest point in his life so far. Let's pick up here in verse 41 of Genesis 27. The Bible says, "So Esau hated Jacob because of the blessing with which his father blessed him. And Esau said in his heart, 'The days of mourning for my father are near; then you will go away that I may kill you.'" Now Rebekah had told her older son Esau, saying: "Surely your brother Jacob has taken a blessing from me." Therefore she sent and called Jacob, her younger son, and said to him: "Surely your brother Esau comforts himself concerning you by intending to kill you. Now therefore, my son, obey my voice: Arise, flee to my brother Laban in Haran and stay with him a few days until your brother's fury turns away from you, until he forgets what you have done to him." Then I will send and bring you from there. Why should I bereaved also of you both in one day? And Rebekah said to Isaac: "I am weary of my life because of the daughters of Heth; if Jacob takes a wife of the daughters of Heth like these who are the daughters of the land, what god will be to me?" Then Isaac called Jacob and blessed him and charged him, saying to him: "You shall not take a wife from the daughters of Canaan. Arise, go to Padan Aram to the house of Bethuel, your mother's father, and take yourself a wife from there of the daughters of Laban, your mother's brother. And may God Almighty bless you and make you fruitful and multiply you, that you may be an assembly of peoples, and give you the blessing of Abraham, to you and your descendants with you, that you may inherit the land in which you are a stranger, which God gave to Abraham." So Isaac sent Jacob away, and he went to Padan Aram, to Laban, the son of Bethuel the Syrian, the brother of Rebekah, the mother of Jacob and Esau. Let us go now in prayer. Father, we thank You for Your word. Lord, open our eyes that we may see wonderful things from Your law. In Jesus' name, amen. Alright, guys. When God meets us in our mess, part two.
Lord, may your kingdom come. May your will be done on earth as it is in heaven, especially within our church and lives. Let us live under the crown of King Jesus. Lord, we pray that if anyone is lost this morning, they would find the gospel irresistible, sweet, and life-changing. Lord, soften hardened hearts, comfort broken ones, warn the idle, and encourage the weak. Edify your people, beautify your bride through the washing of the water of the word. Speak through me, Jesus, make your presence known and felt in our midst today. In Jesus' name, amen. Alright, guys. When God meets us in our mess, part two.
Now, as we continue in our study of this family, let us remember that even amidst their dysfunction, God is present and His purposes are never thwarted. Last week, we examined one of the most troubled families in Scripture, a family marked by favoritism, deception, false repentance, brotherly hatred, and even a murder plot. We saw Isaac favoring Esau and Rebekah favoring Jacob, witnessed Jacob's cunning deception to steal his brother's blessing, and observed Esau's tears of regret rather than godly sorrow. It was indeed messy, but we had to confront the depths of their family dysfunction. We ended with the truth that God's sovereign purposes are never thwarted by our sin, and He chose Jacob to carry on the covenant line not because of Jacob's worthiness, but because of His faithfulness to His promises. We also discussed how sin causes disruption in our harmony with God and each other, and it's only through the gospel that this harmony can be restored.
And the good news is we will one day see reconciliation take place. Oh, but not yet. Not yet. We have many, many years until we see that. In fact, we're going to see 20 years take place in Jacob's life before he is one day reconciled to his brother Esau. But you didn't see that coming. But I get ahead of myself, right? For now, we see that Jacob has the blessing. But he's lost everything else. He flees for his life from a brother who wants him dead. He leaves his parents. He leaves his home. He leaves everything comfortable, everything familiar. And we'll see that God takes him on a journey to break him and then to rebuild him into the man God has called him to be.
Now, this morning, you may be asking, "Is there any hope for me? Can God meet me in the midst of my own brokenness and despair?" Can God help me deal with the consequences of my own sinful actions?" Because that's exactly what Jacob is dealing with this morning. This partly his fault. But yet, we see that God is going to meet him in his lowest point. So this morning, if you feel broken and desperate and alone, if you're wondering, "Has God given up on me? Can God meet me where I am?" Well, here's the good news: God is going to meet us in our brokenness. He's not waiting for us to have it all together. He meets us right where we are.
So let's first look at Jacob's journey into brokenness. In chapter 28, Isaac blesses Jacob properly this time, but then sends him away. Yet again, Rebekah eavesdrops, overhearing Esau's promise to kill Jacob. She then helps Jacob flee to her family in Padan Aram, where he must stay until Esau's anger subsides and find a wife among his mother's people. Unknowingly, Rebekah's scheming sends Jacob away for 20 years; she'll never see him again, losing both sons that day—her relationship with Esau is also severed as he moves to the mountains of Seir. Despite this, God promises to meet Jacob in his lowest point, offering hope even amidst sin's consequences.
She would never see his face again. Friends, that's the far-reaching consequences of sin, isn't it? It takes us farther than we want to go, keeping us longer than we want to stay. This is why, in our brokenness and sin, God's presence and promises of salvation are all the more precious. They offer a way back, a ladder to climb out of the pit we've dug for ourselves through Jacob's example.
And friends, we will never get ahead in life by living contrary to God's design. Never. Just look at Jacob, he has the blessing but he's leaving everything behind. He's fleeing his brother's murderous rage, leaving his mother who loves him so much, heading to an unknown land. He should think, "I've won, I've got what I always wanted," but Jacob never felt more like a loser in his life. But here's where God steps in. He's leading Jacob to the place where he will learn his lesson because, as Galatians 6 tells us, "Do not be deceived: God is not mocked. Whatever a man sows, that also he will reap." Ultimately, Jacob is going to Laban, Rebekah's brother, to be his uncle, and there he will reap what he has sowed. He deceived his father, and now he will be deceived multiple times by his father-in-law. It's a harsh reality, but it's God's way of teaching Jacob—and us—that our actions have consequences. So let's learn from Jacob's mistakes and turn to Jesus, the only one who can save us from ourselves.
"And he's going to serve 14 years for two wives, then another six. He'll face an even greater manipulator than himself. Galatians 6 says, 'Don't be deceived; God is not mocked.' Whatever a man sows, that shall he also reap. Jacob deceived his father, so now he will be deceived multiple times by his father-in-law. As Jacob will soon discover, his actions have consequences."
Remember how Jacob deceived his father? With goat skins, right? Well, years later, when Jacob has sons of his own, they use goat's blood on their brother Joseph's clothes, deceiving him into believing Joseph is dead. So we see a full circle here - deception by goats and clothing. Jacob truly reaps what he sowed. But God isn't out to destroy us with our sins; He breaks us, humbles us, and brings us to repentance so we can find hope in the gospel. Now, Jacob is at his lowest point, as verse 10 tells us.
And now, Jacob leaves Beer-sheba, heading towards Haran. As night falls, he stops at a place, uses a stone for a pillow, and sleeps there. He must've been exhausted. That night, he dreams of a ladder reaching from earth to heaven, with angels ascending and descending on it. Quite the dream, isn't it? Let's pause here for a moment.
And now Jacob went out from Beersheba, weary from his journey, and headed toward Haran. As the sun began to set, he came upon a certain place where he decided to spend the night. Exhausted, he took one of the stones there and placed it under his head as a makeshift pillow. Lying down in that spot, he must have been incredibly tired, for he soon drifted off into a deep sleep. Little did he know, this was no ordinary night. For as he slept, he began to dream a most remarkable dream. Behold, there before him stood a ladder, its top reaching up to the very heavens itself. And what do you suppose he saw? Angels of God ascending and descending upon it, going about their heavenly business. What a sight to behold! This was no mere figment of his imagination; this was a glimpse into the very presence of God, a promise of His constant companionship and care. Let us pause here for a moment and consider the wonder of it all.
Let's consider Jacob now, God's chosen but wayward son, once soft and smooth in his mother's garden, now a fugitive in the wilderness. This is not his territory; this is where hunters go, not gardeners. He's on a 50-mile journey to Padan Aram, approximately halfway through, perhaps on his second night. Exhausted, he comes to a certain place, later known as Luz, or Bethel, where his grandfather Abraham once set up an altar. Jacob takes a stone from the ground and uses it as a pillow beneath his head. As he closes his eyes, he begins to dream. Behold, a ladder stands firmly on the earth, its top reaching up to heaven. Angels of God ascend and descend upon it, their wings stirring the air with a rustling like whispers of divine conversation. This is no ordinary dream; this is a vision of God's presence and promise, a lifeline stretching from Jacob's desperate circumstance to the very throne of heaven.
And we'll later know that place is called Luz. Luz simply means 'almond tree'. Little does he know that his grandfather, Abraham, had been to this very spot years before, setting up an altar here. It would later be known as Bethel, the House of God. Abraham had stood right where Jacob now lies, encountering God's presence in a profound way. Yet, Jacob seems unaware of this history, perhaps even ignorant of its significance. Little does he know that God is about to meet him here at his lowest and most desperate moment. Exhausted, he takes a stone, places it under his head as a makeshift pillow, and prepares to sleep under the vast, indifferent heavens. But unbeknownst to him, he's not alone. The God who walked with Abraham is about to reveal Himself in the darkness, offering Jacob hope amidst his despair.
Now picture this. He's alone, without the love of his mother to comfort him, with the hatred of a brother who wants him dead, and the disgrace of a deceived father. Back home, he had riches, food, anything he wanted. Now, he only has what he can carry. He's made mistakes, exhausted, desperate. He's stolen covenant promises, yet has nothing to show for them despite his former wealth and status. Nothing at all. He's a fugitive, with the heavens as his canopy and the stars as his only source of light. Lying on the dark, cold, damp ground, no doubt he's thinking, "Lord, how did I get here? Why did I do this?" Using a stone for a pillow, God is present even in his despair, offering promises of salvation to this broken man.
He's in an impossible situation, literally and figuratively. He's lost everything—his wealth, his family, even his sense of self-worth. He's a man who's betrayed his own brother, stolen his father's blessing, and now lies alone on the cold ground, staring up at the stars he once thought were promised to him. He has no impressive spiritual resume, only a heart heavy with guilt and deceit. He's a lying manipulator, a deceiver who's thrown away everything for a fleeting moment of power. Now, he's left with nothing but regret and desperation, wondering how he could have fallen so far from grace.
And no doubt, he's just lying there on his back. The stars above twinkle like ice chips in a broken mirror, mocking him with their countless numbers while he has nothing. He's looking up at them, probably heard his dad talk about God's promise to his grandfather, how he'd have descendants as many as the stars in the sky. But now, he's left with an empty chest, his heart heavy with regret. "What have I done?" he thinks, his breath coming in ragged gasps, like a man who's been running for his life from his own mistakes. And that, right then, is when God shows up. Maybe you've had some of those moments too, flat on your back, wondering how you ended up there, what you've done to deserve it. That's when God chooses to reveal Himself, isn't He? Now we look.
In verse 10 through 15, God appears to him in a dream. Verse 12, he dreams a vivid dream. And there it stands, the ladder, an awe-inspiring sight connecting heaven and earth. Angels are ascending and descending upon it, their wings stirring the air with whispers of divine activity. Now, what is this ladder? Literally, in the Hebrew, it's not just any ladder; it's sulam, a word so rare it appears only once in the entire Old Testament. It's not merely a ladder, but a stairway, a bridge spanning the chasm between a holy God and a desperate, sinful man like Jacob. The angels ascending and descending upon it speak of God's constant presence, His promises active even now, even here. So, what does this mean for Jacob? For us? It means God is saying, "Jacob, I am still with you. My angels are here to protect you, to guide you. Even at your lowest point, in your despair and desperation, I am with you." It's the opposite of the Tower of Babel, where man reaches for the heavens in pride. Here, God reaches down to Jacob in grace, bridging the gap between them with a ladder of love.
It means God is saying, Jacob, I'm still with you. My angels are here to protect you. I'm giving you my presence and I'm giving you my promises. You may feel unworthy, like a scoundrel, but remember, none of us deserve such grace. Yet, even at your lowest point, I am with you. This vision is the antithesis of the Tower of Babel in chapter 1. There, humanity tried to reach God; here, God reaches out to Jacob, bridging the gap between a holy God and sinful man. I demand your attention: God is calling out to you today, offering his presence and promises, just as he did to Jacob.
Didn't really work in chapter 1 either, did it? But we notice that when Jacob cannot make his way to God, what does God do? God makes His way to him. He cannot go up, so God must come down. In verse 13, behold, the Lord stood above it, and the Lord says, "I am the Lord, Yahweh." That's His covenant name. "I am the God of Abraham, your father, and the God of Isaac." Now, I've learned this fascinating thing. It says, "the Lord stood above it," but in Hebrew, it can also mean "the Lord stood beside it." In other words, God was at Jacob's side as he lay on the ground, sleeping on a pillow. God is with him. God has come to earth, as it were. How awesome is that? Some of you are starting to make connections. Some of you see where this is going. I love it.
Man, I love it! When Jacob can't reach God, God comes down to him, revealing himself as the covenant-keeping, promise-keeping God. He begins to bless Jacob, saying, "The land on which you lie, I will give to you and your offspring. Your offspring shall be like the dust of the earth, spreading abroad in all directions. In you and your offspring, the families of the earth shall be blessed." Then he promises, "I am with you; I will keep you wherever you go and bring you back to this land. For I will not leave you until I have done what I promised."
This is the Abrahamic covenant, reiterated now to Jacob: a people, a place, and a promise. But the most precious gift God gives is his presence. He assures Jacob, "I am with you," echoing the writer of Hebrews' words that he will never leave us or forsake us. Despite Jacob's struggles, God blesses him not because of his worthiness but because God is faithful to his promises.
And what's more, God gives Jacob the greatest blessing: himself. He says, "Jacob, I am with you; my presence is the ultimate blessing." Believer, this promise is for you too—God will never leave or forsake you, even at your lowest. As Jacob awakens, he realizes, "Surely the Lord is in this place, and I did not know it." He thought he was alone, but God was with him all along.
And then he gives him the greatest blessing of all. Not his promises, but his presence. He says, "I am with you, Jacob." All your life, you thought you needed things to be successful. You thought you needed me, material blessings and possessions, and you were willing to do anything to get them. But Jacob, the greatest blessing I can give you is myself. The greatest blessing anyone can receive is the presence of God with them. And God is saying, "Jacob, I will never leave you. I will never forsake you. I will make sure all of my promises come true." Believer, that is a promise for you as well. He will finish what he started. He will never leave you or forsake you, even at your lowest. Jacob's response in verse 16: "Jacob awoke from his sleep and said, 'Surely the Lord, Jehovah, is in this place,' and I did not know it."
He thought he'd forfeited God's blessing through his deception. "Man," he thinks, "it can't get any worse. Surely God's going to abandon me now. I've messed up, lost everything." But God says, "Oh no, boy. I'm still with you." Praise God! Friends, how many of us have felt that way? We think, "Surely God can't be with me now. I've blown it too many times." But that's when God shows up, isn't it? Not just on the mountaintop, but in the valley. In fact, I believe it's in times of brokenness and loneliness, heartache—that's when God shows up strongest and sweetest. When we're at our worst, that's when God is at his best. He finds us even when we're sleeping on rocks.
He'll find you even in your darkest hour, friends. When you've made a mess of your life, God is still there, reaching out to you with mercy and grace that knows no end. So hear me this morning: God's grace is greater than all of your sin. You will never be able to out-fail or out-sin the grace and mercy of God. It's impossible; you'll never exhaust his love for you, nor his mercy towards sinners. Praise God for that! Jacob exclaimed, "How awesome is this place!" (Verse 17). This, he realized, was none other than the house of God, the very gate of heaven. And so, he took the stone he'd used as a pillow and set it up as a pillar, pouring oil on it. Now, that's not just a play on words, okay? I know some of you old folks might say 'pillar' for 'pillow', but this morning, we're awake and alert!
Y'all laugh. That's a joke, right? It wasn't in my notes, I promise. But you know what's not a joke? The fact that Jesus Christ is the way we experience God's presence today. Just like Jacob made his pillow into a pillar to remember God's presence, we can make Jesus our foundation, our memorial of His presence in our lives. And just as Jacob poured oil on his pillar and named it Bethel, meaning "house of God," we too can invite Him into our hearts and lives. Now, let's talk about what that means for us today...
A monument. A memorial of the God's constant presence. He pours oil on it, anointing it, and names the place Bethel - "House of God." This isn't just any house; it's where God dwells, where heaven and earth meet. It's a reminder that even in our darkest times, God is with us. Now, anyone want to guess why this is so significant? You've already got the answer: Jesus Christ. He's the ladder, the bridge between heaven and earth, offering us salvation. So, let's step onto that ladder, brothers and sisters, and experience the urgent, passionate presence of our God.
House of God. There we go. It's God's house. God is with him. Abraham, his grandfather, had camped here and built an altar here before. Years later, the same God is here. Now, notice this: The place hasn't changed. The stone hasn't changed. His circumstances haven't even changed. But he shifts his gaze, urgently turning away from his problems, and fixes it upon the One who can truly fix them. Right?
He says, now, God is here. And a place, once ordinary, becomes hallowed ground when we recognize his presence. It's no longer just a location; it becomes the house of God. Isn't that remarkable? When our lives, once marked by brokenness and despair, become living testaments to his grace as he transforms us from within? That's exactly what happens here. God shows up in our ordinary, hard, broken places, inviting us to step into a new reality with him.
When my brokenness is laid bare, God steps in, transforming it into a resounding testimony of His grace. When despair meets divine intervention, it becomes a powerful declaration of His presence. That's precisely what God does here; He shows up in our ordinary, hard, broken places, turning our stories into declarations of His faithfulness.
**Corrected Paragraph:**
Jacob's vow, recorded in verses 20 through 22, is a poignant expression of his desperation and faith in God's presence and provision amidst his trials. He boldly declares, "If God will be with me and keep me in this way that I am going, and give me bread to eat and clothing to wear, then the Lord shall be my God." Jacob knew how to bargain, even with God, didn't he? His faith was conditional, yet it was faith nonetheless. He clung to God's promise made 20 years prior, "I will bring you back," and looked forward to its fulfillment for his descendants, the Israelites in Egypt centuries later.
God had already promised to return Jacob to Canaan, but Jacob wanted reassurance. So he vowed, "If You keep Your word, Lord, if You do exactly as You promised, then the Lord shall be my God." He would set up this stone pillar as a reminder of his vow and give a tenth of all that God gave him, a tithe. Jacob's faith was not perfect; it was transactional, an "if-then" deal. Yet, it was here that Jacob placed his faith in the God of Israel, the God of Isaac, the God of Abraham.
That God would surely bring us back to the land of Canaan, the very land He promised to our forefather Jacob, with a near and far fulfillment in His divine plan. But Jacob, in his desperation, cries out, "Lord, if You keep Your word, if You fulfill Your promise, then I will make this stone a pillar, a symbol of Your house, and give You a tenth of all that You bless me with." His faith is raw, transactional even, an 'if-then' bargain born from the depths of his need. Yet here, in this moment, Jacob's eyes are opened to the God of Israel, the God of Isaac, the God of Abraham. He's not perfect, his faith is a flickering flame, but it's real, burning against the cold night of his exile.
He's committing himself to the God who had committed himself to him. Saying, Lord, if you'll keep your word. You'll be my God. Now, he doesn't have everything figured out. He's as much like us. He has doubts. He has questions. He has imperfect trust. Friends, God is not looking for you to have all the answers. He's looking for you to take the measure of faith that he's given you. Take the oil and pour it out on the rock and say, Lord, I trust you to keep your word.
You're my God. The Lord saves him. Indeed, there is much work to do now that Jacob has begun his life with God through faith in Jesus Christ.
Because God must also subdue him and separate him and sanctify him. It's going to take 20 years to do this. But now, Jacob, he's beginning his life with God. This is a new beginning for him.
The house of God, the gateway to heaven, is indeed the gateway to his new life. And God, through it all, will keep His promises; He will bring Jacob back to the land.
---
**Internal Adversarial Review:**
*Editor Pass:*
- Collapsed repeated "he wil" to "He will"
- Changed "al" to "all"
- Added commas for clarity
*Auditor Pass:*
- Checked for added ideas or theology: None found
- Checked for removed unique ideas: None found
- Checked for altered meaning: Meaning preserved
- Checked for softened theological force: Theological force preserved
- Checked for reordered arguments: Argument structure preserved
- Checked for missed transcription loops: No repetition remains
- Checked for unnecessary over-editing: Minimal editing, preserving original tone and voice
**Final Loop Check:**
No mechanical repetition remains.
**Output:**
The house of God, the gateway to heaven, is indeed the gateway to his new life. And God, through it all, will keep His promises; He will bring Jacob back to the land.
Now, we could end here, and that would be a good story of God keeping his promises, right? Of God showing grace to broken, undeserved people. But, oh man, it gets so much better.
Where do we see Jesus in this passage? Because if we don't see Jesus, there is no gospel message. And I want you to do this with me. Turn in your Bibles to the book of John, chapter 1, beginning in verse 43. I'll tell you what, I've been so excited all week to bring this out. It's like, man, this is awesome. This might be new information for some of you; some of you have probably heard it before. But, man, it's so good. John, chapter 1, beginning in verse 43. I'll give you a second to get there because you all need to track with this.
*Collapsed repeated phrases and corrected minor transcription errors while preserving meaning, tone, and emphasis.*
Now, this early in Jesus' ministry, as He sets out for Galilee, He finds Philip and says, "Follow me." This is the calling of the disciple Philip. Notably, Philip hails from Bethsaida, the city of Andrew and Peter, indicating that Jesus is indeed calling some of His first disciples. And true to form, Philip begins telling others about Jesus, seeking to make more disciples. He finds his friend Nathanael and shares, "We have found him of whom Moses in the law and also the prophets wrote, Jesus of Nazareth, son of Joseph." Yet Nathanael responds skeptically, "Can anything good come out of Nazareth?" Philip's reply is urgent and passionate: "Come and see for yourself, old friend. You don't even know!"
As Nathanael approaches, Jesus sees him coming and exclaims, "Behold, an Israelite indeed, in whom is no deceit!" Here, Jesus underscores the purity and sincerity of Nathanael's heart, a testament to God's presence and favor upon him. This moment, dear congregation, is a vivid illustration of our thesis: there is no greater blessing than experiencing God's personal, intimate presence, as seen in Jesus' immediate recognition and affirmation of Nathanael. So, let us strive to cultivate such sincerity and openness before the Lord, that we too may experience His divine favor and blessing.
Nathanael was astonished. "How do you know me?" he asked, his voice filled with wonder and disbelief. And Jesus answered him, not with a simple reply, but with a profound revelation: "Before Philip even called you, while you were sitting under the fig tree, I saw you. It's as if I stood beside you in that very moment." Nathanael's astonishment deepened; it was not just surprise anymore, but a sense of awe and reverence. He addressed Jesus with newfound respect, "Rabbi, you are the Son of God! You are the King of Israel!" Jesus' response was not one of boasting, but of invitation: "Because I said to you, 'I saw you under the fig tree,' do you believe? You will see much greater things than these." And then, with a tone that was both assuring and awe-inspiring, Jesus declared, "Most assuredly, I say to you, hereafter you shall see heaven open and the angels of God ascending and descending on the Son of Man." Nathanael could hardly contain his excitement. He felt a profound sense of connection to something far greater than himself. And with a heart full of joy and anticipation, he exclaimed, "Amen! And hallelujah!"
I know it might be sleepy and rainy outside, but come on, somebody, let's not miss this moment. Who is that ladder? Let me rewind for you. Thousands of years ago, Jacob had his dream under a fig tree, and now here we are with Nathanael, sitting under another fig tree, the customary spot for reading God's law and meditating. Imagine the scene: the rustling leaves, the scent of damp earth after rain, Nathanael's eyes scanning the familiar words of Genesis 28. He's probably wondering, "How can I know that God is with me here in this backwater town?" Enter Jesus, called by Philip, ready to change everything.
And then Philip brings Jesus and introduces him as Jesus of Nazareth, the one that the Scriptures have prophesied about. And Nathanael says, "Nazareth? Can anything good come out of Nazareth?" And Jesus, with urgency in his voice, responds, "You are a son of Israel, remember? The name later given to Jacob, the man here in Genesis 28. You're a son of Israel, not like your father Israel who was a deceiver, a conniver, a manipulator. No, you are a man looking for truth." Jesus' tone is passionate as he continues, "And here I am, standing before you, the ladder between heaven and earth that you've been reading about."
You're questioning how God's presence could possibly be with you, Nathanael. We can only imagine all these thoughts racing through your mind. And then, you ask Jesus, "How do you know me? We've never met." Jesus responds with urgency, "Listen, before Philip even called you, I saw you under the fig tree. I knew your heart's desire, Nathanael. But if you refuse to believe, what will become of you?"
And by the way, I know what you were reading. Why? Because just as God was beside Jacob, God was with Nathanael. Jesus was right there with him, present in his life even before Nathanael knew it. This is how Jesus shows us that he is indeed the ladder between God and man, the one who connects a holy God in heaven with sinful men on earth, just as Jacob saw in his dream. Nathanael becomes a believer because of this personal, intimate presence of God in his life.
He confesses, "You are the Christ, the Son of the living God." You're not just a rabbi or a god teacher or a god man. You are the Messiah. And Jesus says, "You haven't seen anything yet. One day you'll see the heavens open and you'll see the angels of God ascending and descending on the Son of Man." What is Jesus saying? He's saying, "I am the ladder that Jacob dreamed about. Remember, this was a vision given to him by God in his dream. I am that ladder that connects a holy God in heaven with sinful man on earth. I am the bridge between God and man. And the angels of God ascend and descend on me." What does that indicate? I believe it indicates his heavenly origin, he's the Son of God from heaven, but also pictures his return in glory when he returns with the angels in power. So let's discuss how Jesus' divine nature bridges the gap between God and humanity, fulfilling Jacob's ladder vision as a preview of his mediatory role, as seen in 1 Timothy 2:5.
How Jesus is the bridge between God and humanity, as depicted in Jacob's ladder dream. It was merely a preview, a promise of what God would accomplish through His Son. In 1 Timothy 2:5, we learn that "there is one mediator between God and men, the man Christ Jesus." Fully divine in essence yet truly human without sin, Jesus spans the chasm created by sin, reconciling us to God. He is our go-between, our mediator, bridging the gap that religion cannot traverse.
He is the go-between. He is the mediator. He is the one who reconciles us to God. Friends, he does what religion cannot do. So many people are attempting to climb their way to God with all their might, in their own efforts, right?
They're building their own towers of Babel, trying to be god enough. Trying to clean themselves up, trying to climb the ladder with all their might. And then, their foot slips.
They fall back into sin, toppling all the way down to where they started. It's just exhausting. You can't make your way up to God on your own strength. But God does for us what we cannot do for ourselves. He comes down to meet us, as Jesus did with Jacob, bridging the gap between us and Himself in love.
When we can't reach him, he comes down to us, right? And all of us are like Jacob. We're deceptive, self-serving, unworthy of nothing but judgment. There's a gap between us and God that we can't cross on our own. But then Jesus comes down, bridging the chasm with his incarnation. He meets us in our mess, in our brokenness, while we're sleeping on rocks or stuck between a rock and a hard place. And he sends Emanuel, God with us, leaving the glories of heaven to walk the dust of the earth, to go to the cross, to be buried, and to rise again. As A.W. Pink puts it, "Right down where the fugitive lay, the ladder came, and right up to God himself the ladder reached." Praise be to God!
The Bible tells us in John 1, verse 14 that the Word became flesh and dwelt among us. God crossed the gap that we couldn't cross. He meets us in our messes, in our brokenness. While we are sleeping on rocks, while we are stuck between a rock and a hard place, God sends Emanuel—God with us. He leaves the glories of heaven to walk the dust of the earth, to go to the cross, to be buried, and to rise again. I love what A.W. Pink says: "Right down where the fugitive lay, the ladder came. And right up to God Himself, the ladder reached." Praise God! For it is in Jesus Christ that we find the greatest blessing—the presence of God—and this can only be experienced through faith in Him.
The cross wedged in the dirt of earth with Jesus, the Son of God hanging upon it in the expanse, bridges the gap between a holy God and sinful man. He is the ladder. He is the way. Jesus says in John 14, 6, "I am the way, the truth, and the life. No one comes to the Father except through me." Indeed, Jesus is not merely a means to an end; he is the very way. Just as there is but one way to heaven, it's only one ladder. Right? It's only one way.
There is only one bridge between a holy God and sinful man. Jesus Christ, the Son of God, is that bridge, just as He was the ladder in Jacob's dream. When we cross this bridge, we cross over from darkness to light, from death to life, from condemnation to justification. This crossing is not merely about transition but about encountering God's presence, His greatest blessing for us.
From brokenness to healing. Remember what I said earlier, remember what Bethel means – it's the house of God. And who is Jesus but God with us? Even before his birth, it was prophesied that he would be named Emanuel, God with us, as Matthew 1:23 tells us. Friends, Jesus is the ultimate house of God, his presence among us. He came down to earth for this very purpose. And as believers, we are told in 1 Corinthians 3:16 that we are the temple of the Holy Spirit, and God dwells in us. So, we need not ask like Jacob did, "Is God in this place?" For if you are a believer, he is indeed in you, with you always. You are Bethel – the house of God.
You have the greatest blessing imaginable living within you—the constant presence of God Himself. And if you are a believer, you need not question whether God is with you; He is indeed present, and His promise in Hebrews 13:5 assures us that "He will never leave you nor forsake you." Even when we find ourselves broken sinners, like Jacob on the run, God remains beside us. He is the Good Shepherd seeking the lost sheep, having not abandoned us to our sin or left us alone in our wilderness. Consider Jacob's plight—he was a lost sheep, yet here was God coming to his rescue as his shepherd, bestowing exceedingly great and precious promises upon him. The same holds true for us today; as a word of application, number one, God meets broken people where they are.
He doesn't wait for us to clean up ourselves. To somehow stop doing this and stop doing that so we're presentable. No, he comes to fix us in our brokenness, right? Jacob was a mess, a liar, a deceiver, a manipulator—he's running from God with his life on the line. Maybe you've done all these things and worse, thinking it can't get any worse, that there's no way God could ever receive you. But friends, God has already made the way for you to be forgiven, to be received, to receive his salvation right now. You just need to repent of your sins and place your faith in Christ. Just step onto that ladder, and he'll take you the rest of the way up.
Secondly, God gives us his presence and his promises. Yes, he gives us exceedingly great and precious promises, eternal promises. He promises us forgiveness and justification and a home in heaven. But the greatest promise is his presence. The promise that neither life nor death nor angels nor rulers nor things present nor things to come nor powers nor height nor depth nor anything in all creation. Nothing will be able to separate you from the love of God that is in Christ. God was with Jacob. God will be with you. Friends, will you respond in faith? Will you realize that the ladder has come down from heaven? He has reached out to you. Will you by faith step on this ladder?
The Lord Jesus Christ, as He extends His invitation through the song of His people. Take a moment, I urge you, to reflect upon the message shared today. Let this be a time for prayer and contemplation in your heart.
And if you would like someone to come and pray for you, pray with you, please approach me or a friend here. Come to the one who has come down to you, Jesus Christ, ready to lift you up in your time of need.
"""

polished_sermon = """
When God Meets Us in Our Mess, Part Two

15 February, 2026
Thesis: God's presence is the greatest blessing He can offer to humanity, and it is only through faith in Jesus Christ that we can experience this presence, which bridges the gap between a holy God and broken, sinful humanity.

Summary: The sermon, titled "When God Meets Us in Our Mess, Part Two," recounts Jacob's flight from Esau after his deception, emphasizing the consequences of his actions and God's allowance for individuals to experience the results of their sin as a path to repentance. In his desperate state, Jacob dreams of a ladder connecting heaven and earth, where God appears to him, reiterating the Abrahamic covenant and promising His unfailing presence. This encounter leads to Jacob's vow of faith, signifying a turning point. The sermon then interprets Jacob's ladder dream through John 1, where Jesus declares Himself to be the fulfillment of this vision, the sole bridge and mediator connecting a holy God and sinful humanity. The concluding application underscores that God meets broken individuals in their struggles, offering His presence and promises through Jesus Christ.

Oh, you are good. Indeed, alright. Well, thank you all for leading us in worship this morning. It's always a blessing to have you with us. See, this morning, let us look into the book of Genesis, chapter 27.

Did y'all enjoy the worship led by the Bruner family this morning? I sure did, as they brought a powerful reminder of God's presence with us today. It was truly a blessing to have them here, and their ministry serves as a testament to the promises of salvation that God extends to broken and sinful individuals like you and me.

Now, let's turn our attention to God's Word this morning, as we look into Genesis, chapter 27.

We shall resume where we left off last week. Now, before we proceed, let me remind you that we dismissed our children for Children's Church today. I apologize if I overlooked mentioning that earlier.

Turning to Genesis chapter 28 this morning, we'll begin in verse 47.

And if you remember, this is part two of 'When God Meets Us in Our Mess', part two. And this is when God meets Jacob at his lowest point in his life so far. Let's pick up here in verse 41 of Genesis 27.

The Bible says, "So Esau hated Jacob because of the blessing with which his father blessed him. And Esau said in his heart, 'The days of mourning for my father are near; then you will go away that I may kill you.'" Now Rebekah had told her older son Esau, saying: "Surely your brother Jacob has taken a blessing from me."

Therefore she sent and called Jacob, her younger son, and said to him: "Surely your brother Esau comforts himself concerning you by intending to kill you. Now therefore, my son, obey my voice: Arise, flee to my brother Laban in Haran and stay with him a few days until your brother's fury turns away from you, until he forgets what you have done to him."

Then I will send and bring you from there. Why should I bereaved also of you both in one day?

Rebekah said to Isaac: "I am weary of my life because of the daughters of Heth; if Jacob takes a wife of the daughters of Heth like these who are the daughters of the land, what god will be to me?"

Then Isaac called Jacob and blessed him and charged him, saying to him: "You shall not take a wife from the daughters of Canaan. Arise, go to Padan Aram to the house of Bethuel, your mother's father, and take yourself a wife from there of the daughters of Laban, your mother's brother.

And may God Almighty bless you and make you fruitful and multiply you, that you may be an assembly of peoples, and give you the blessing of Abraham, to you and your descendants with you, that you may inherit the land in which you are a stranger, which God gave to Abraham."

So Isaac sent Jacob away, and he went to Padan Aram, to Laban, the son of Bethuel the Syrian, the brother of Rebekah, the mother of Jacob and Esau.

Let us go now in prayer. Father, we thank You for Your word. Lord, open our eyes that we may see wonderful things from Your law. In Jesus' name, amen.

Alright, guys. When God meets us in our mess, part two.

Lord, may your kingdom come. May your will be done on earth as it is in heaven, especially within our church and lives. Let us live under the crown of King Jesus.

Lord, we pray that if anyone is lost this morning, they would find the gospel irresistible, sweet, and life-changing. Lord, soften hardened hearts, comfort broken ones, warn the idle, and encourage the weak. Edify your people, beautify your bride through the washing of the water of the word. Speak through me, Jesus, make your presence known and felt in our midst today.

Alright, guys. When God meets us in our mess, part two.

Now, as we continue in our study of this family, let us remember that even amidst their dysfunction, God is present and His purposes are never thwarted. Last week, we examined one of the most troubled families in Scripture, a family marked by favoritism, deception, false repentance, brotherly hatred, and even a murder plot.

We saw Isaac favoring Esau and Rebekah favoring Jacob, witnessed Jacob's cunning deception to steal his brother's blessing, and observed Esau's tears of regret rather than godly sorrow. It was indeed messy, but we had to confront the depths of their family dysfunction.

We ended with the truth that God's sovereign purposes are never thwarted by our sin, and He chose Jacob to carry on the covenant line not because of Jacob's worthiness, but because of His faithfulness to His promises.

And the good news is we will one day see reconciliation take place. Oh, but not yet. Not yet.

We have many, many years until we see that. In fact, we're going to see 20 years take place in Jacob's life before he is one day reconciled to his brother Esau. But you didn't see that coming.

But I get ahead of myself, right? For now, we see that Jacob has the blessing. But he's lost everything else. He flees for his life from a brother who wants him dead. He leaves his parents. He leaves his home. He leaves everything comfortable, everything familiar.

And we'll see that God takes him on a journey to break him and then to rebuild him into the man God has called him to be.

Now, this morning, you may be asking, "Is there any hope for me? Can God meet me in the midst of my own brokenness and despair?"

Can God help me deal with the consequences of my own sinful actions?" Because that's exactly what Jacob is dealing with this morning. This partly his fault. But yet, we see that God is going to meet him in his lowest point.

So this morning, if you feel broken and desperate and alone, if you're wondering, "Has God given up on me? Can God meet me where I am?"

Well, here's the good news: God is going to meet us in our brokenness. He's not waiting for us to have it all together. He meets us right where we are.

So let's first look at Jacob's journey into brokenness. In chapter 28, Isaac blesses Jacob properly this time, but then sends him away. Yet again, Rebekah eavesdrops, overhearing Esau's promise to kill Jacob. She then helps Jacob flee to her family in Padan Aram, where he must stay until Esau's anger subsides and find a wife among his mother's people.

Unknowingly, Rebekah's scheming sends Jacob away for 20 years; she'll never see him again, losing both sons that day—her relationship with Esau is also severed as he moves to the mountains of Seir. Despite this, God promises to meet Jacob in his lowest point, offering hope even amidst sin's consequences.

She would never see his face again. Friends, that's the far-reaching consequences of sin, isn't it? It takes us farther than we want to go, keeping us longer than we want to stay.

This is why, in our brokenness and sin, God's presence and promises of salvation are all the more precious. They offer a way back, a ladder to climb out of the pit we've dug for ourselves through Jacob's example.

And friends, we will never get ahead in life by living contrary to God's design. Never. Just look at Jacob, he has the blessing but he's leaving everything else. He's fleeing his brother's murderous rage, leaving his mother who loves him so much, heading to an unknown land.

He should think, "I've won, I've got what I always wanted," but Jacob never felt more like a loser in his life. But here's where God steps in. He's leading Jacob to the place where he will learn his lesson because, as Galatians 6 tells us, "Do not be deceived: God is not mocked. Whatever a man sows, that also he will reap."

Ultimately, Jacob is going to Laban, Rebekah's brother, to be his uncle, and there he will reap what he has sowed. He deceived his father, and now he will be deceived multiple times by his father-in-law.

It's a harsh reality, but it's God's way of teaching Jacob—and us—that our actions have consequences. So let's learn from Jacob's mistakes and turn to Jesus, the only one who can save us from ourselves.

"And he's going to serve 14 years for two wives, then another six. He'll face an even greater manipulator than himself."

Galatians 6 says, 'Don't be deceived; God is not mocked.' Whatever a man sows, that shall he also reap. Jacob deceived his father, so now he will be deceived multiple times by his father-in-law.

Remember how Jacob deceived his father? With goat skins, right? Well, years later, when Jacob has sons of his own, they use goat's blood on their brother Joseph's clothes, deceiving him into believing Joseph is dead.

So we see a full circle here - deception by goats and clothing. Jacob truly reaps what he sowed. But God isn't out to destroy us with our sins; He breaks us, humbles us, and brings us to repentance so we can find hope in the gospel.

Now, Jacob is at his lowest point, as verse 10 tells us.

And now, Jacob leaves Beer-sheba, heading towards Haran. As night falls, he stops at a place, uses a stone for a pillow, and sleeps there. He must've been exhausted.

That night, he dreams of a ladder reaching from earth to heaven, with angels ascending and descending on it. Quite the dream, isn't it? Let's pause here for a moment.

And now Jacob went out from Beersheba, weary from his journey, and headed toward Haran. As the sun began to set, he came upon a certain place where he decided to spend the night. Exhausted, he took one of the stones there and placed it under his head as a makeshift pillow.

Lying down in that spot, he must have been incredibly tired, for he soon drifted off into a deep sleep. Little did he know, this was no ordinary night. For as he slept, he began to dream a most remarkable dream.

Behold, there before him stood a ladder, its top reaching up to the very heavens itself. And what do you suppose he saw? Angels of God ascending and descending upon it, going about their heavenly business. What a sight to behold! This was no mere figment of his imagination; this was a glimpse into the very presence of God, a promise of His constant companionship and care.

Let's consider Jacob now, God's chosen but wayward son, once soft and smooth in his mother's garden, now a fugitive in the wilderness. This is not his territory; this is where hunters go, not gardeners. He's on a 50-mile journey to Padan Aram, approximately halfway through, perhaps on his second night.

Exhausted, he comes to a certain place, later known as Luz, or Bethel, where his grandfather Abraham once set up an altar. Jacob takes a stone from the ground and uses it as a pillow beneath his head. As he closes his eyes, he begins to dream. Behold, a ladder stands firmly on the earth, its top reaching up to heaven.

Angels of God ascend and descend upon it, their wings stirring the air with a rustling like whispers of divine conversation. This is no ordinary dream; this is a vision of God's presence and promise, a lifeline stretching from Jacob's desperate circumstance to the very throne of heaven.

And we'll later know that place is called Luz. Luz simply means 'almond tree'. Little does he know that his grandfather, Abraham, had been to this very spot years before, setting up an altar here. It would later be known as Bethel, the House of God.

Abraham had stood right where Jacob now lies, encountering God's presence in a profound way. Yet, Jacob seems unaware of this history, perhaps even ignorant of its significance.

Little does he know that God is about to meet him here at his lowest and most desperate moment. Exhausted, he takes a stone, places it under his head as a makeshift pillow, and prepares to sleep under the vast, indifferent heavens. But unbeknownst to him, he's not alone.

The God who walked with Abraham is about to reveal Himself in the darkness, offering Jacob hope amidst his despair.

Now picture this. He's alone, without the love of his mother to comfort him, with the hatred of a brother who wants him dead, and the disgrace of a deceived father.

Back home, he had riches, food, anything he wanted. Now, he only has what he can carry. He's made mistakes, exhausted, desperate. He's stolen covenant promises, yet has nothing to show for them despite his former wealth and status. Nothing at all.

He's a fugitive, with the heavens as his canopy and the stars as his only source of light. Lying on the dark, cold, damp ground, no doubt he's thinking, "Lord, how did I get here? Why did I do this?"

Using a stone for a pillow, God is present even in his despair, offering promises of salvation to this broken man.

He's in an impossible situation, literally and figuratively. He's lost everything—his wealth, his family, even his sense of self-worth.

He's a man who's betrayed his own brother, stolen his father's blessing, and now lies alone on the cold ground, staring up at the stars he once thought were promised to him. He has no impressive spiritual resume, only a heart heavy with guilt and deceit.

He's a lying manipulator, a deceiver who's thrown away everything for a fleeting moment of power. Now, he's left with nothing but regret and desperation, wondering how he could have fallen so far from grace.

And no doubt, he's just lying there on his back. The stars above twinkle like ice chips in a broken mirror, mocking him with their countless numbers while he has nothing.

He's looking up at them, probably heard his dad talk about God's promise to his grandfather, how he'd have descendants as many as the stars in the sky. But now, he's left with an empty chest, his heart heavy with regret.

"What have I done?" he thinks, his breath coming in ragged gasps, like a man who's been running for his life from his own mistakes.

And that, right then, is when God shows up. Maybe you've had some of those moments too, flat on your back, wondering how you ended up there, what you've done to deserve it. That's when God chooses to reveal Himself, isn't He?

Now we look.

In verse 10 through 15, God appears to him in a dream. Verse 12, he dreams a vivid dream. And there it stands, the ladder, an awe-inspiring sight connecting heaven and earth. Angels are ascending and descending upon it, their wings stirring the air with whispers of divine activity.

Now, what is this ladder? Literally, in the Hebrew, it's not just any ladder; it's sulam, a word so rare it appears only once in the entire Old Testament. It's not merely a ladder, but a stairway, a bridge spanning the chasm between a holy God and a desperate, sinful man like Jacob.

The angels ascending and descending upon it speak of God's constant presence, His promises active even now, even here.

So, what does this mean for Jacob? For us? It means God is saying, "Jacob, I am still with you. My angels are here to protect you, to guide you. Even at your lowest point, in your despair and desperation, I am with you."

It's the opposite of the Tower of Babel, where man reaches for the heavens in pride. Here, God reaches down to Jacob in grace, bridging the gap between them with a ladder of love.

It means God is saying, Jacob, I'm still with you. My angels are here to protect you. I'm giving you my presence and I'm giving you my promises. You may feel unworthy, like a scoundrel, but remember, none of us deserve such grace.

Yet, even at your lowest point, I am with you. This vision is the antithesis of the Tower of Babel in chapter 1. There, humanity tried to reach God; here, God reaches out to Jacob, bridging the gap between a holy God and sinful man.

I demand your attention: God is calling out to you today, offering his presence and promises, just as he did to Jacob.

Didn't really work in chapter 1 either, did it? But we notice that when Jacob cannot make his way to God, what does God do? God makes His way to him. He cannot go up, so God must come down.

In verse 13, behold, the Lord stood above it, and the Lord says, "I am the Lord, Yahweh." That's His covenant name. "I am the God of Abraham, your father, and the God of Isaac."

Now, I've learned this fascinating thing. It says, "the Lord stood above it," but in Hebrew, it can also mean "the Lord stood beside it." In other words, God was at Jacob's side as he lay on the ground, sleeping on a pillow.

God is with him. God has come to earth, as it were.

How awesome is that? Some of you are starting to make connections. Some of you see where this is going. I love it.

Man, I love it! When Jacob can't reach God, God comes down to him, revealing himself as the covenant-keeping, promise-keeping God.

He begins to bless Jacob, saying, "The land on which you lie, I will give to you and your offspring. Your offspring shall be like the dust of the earth, spreading abroad in all directions. In you and your offspring, the families of the earth shall be blessed."

Then he promises, "I am with you; I will keep you wherever you go and bring you back to this land. For I will not leave you until I have done what I promised."

This is the Abrahamic covenant, reiterated now to Jacob: a people, a place, and a promise.

But the most precious gift God gives is his presence. He assures Jacob, "I am with you," echoing the writer of Hebrews' words that he will never leave us or forsake us.

Despite Jacob's struggles, God blesses him not because of his worthiness but because God is faithful to His promises.

And what's more, God gives Jacob the greatest blessing: himself. He says, "Jacob, I am with you; my presence is the ultimate blessing."

Believer, this promise is for you too—God will never leave or forsake you, even at your lowest.

As Jacob awakens, he realizes, "Surely the Lord is in this place, and I did not know it." He thought he was alone, but God was with him all along.

And then he gives him the greatest blessing of all. Not his promises, but his presence. He says, "I am with you, Jacob."

All your life, you thought you needed things to be successful. You thought you needed me, material blessings and possessions, and you were willing to do anything to get them.

But Jacob, the greatest blessing I can give you is myself. The greatest blessing anyone can receive is the presence of God with them.

And God is saying, "Jacob, I will never leave you. I will never forsake you. I will make sure all of my promises come true."

Believer, that is a promise for you as well. He will finish what he started. He will never leave you or forsake you, even at your lowest.

Jacob's response in verse 16: "Jacob awoke from his sleep and said, 'Surely the Lord, Jehovah, is in this place,' and I did not know it."

He thought he'd forfeited God's blessing through his deception. "Man," he thinks, "it can't get any worse. Surely God's going to abandon me now. I've messed up, lost everything."

But God says, "Oh no, boy. I'm still with you." Praise God!

Friends, how many of us have felt that way? We think, "Surely God can't be with me now. I've blown it too many times." But that's when God shows up, isn't It?

Now we look.

In verse 17, Jacob exclaims, "How awesome is this place!" (Verse 17). This, he realized, was none other than the house of God, the very gate of heaven. And so, he took the stone he'd used as a pillow and set it up as a pillar, pouring oil on it.

Now, that's not just a play on words, okay? I know some of you old folks might say 'pillar' for 'pillow', but this morning, we're awake and alert!

Y'all laugh. That's a joke, right? It wasn't in my notes, I promise. But you know what's not a joke? The fact that Jesus Christ is the way we experience God's presence today.

Just like Jacob made his pillow into a pillar to remember God's presence, we can make Jesus our foundation, our memorial of His presence in our lives.

And just as Jacob poured oil on his pillar and named it Bethel, meaning "house of God," we too can invite Him into our hearts and lives.

Now, let's talk about what that means for us today...

The house of God, the gateway to heaven, is indeed the gateway to his new life. And God, through it all, will keep His promises; He will bring Jacob back to the land.

Now, we could end here, and that would be a good story of God keeping his promises, right? Of God showing grace to broken, undeserved people.

But oh man, it gets so much better.

Where do we see Jesus in this passage? Because if we don't see Jesus, there is no gospel message. And I want you to do this with me. Turn in your Bibles to the book of John, chapter 1, beginning in verse 43.

I'll tell you what, I've been so excited all week to bring this out. It's like, man, this is awesome. This might be new information for some of you; some of you have probably heard it before. But, man, it's so good.

John, chapter 1, beginning in verse 43. I'll give you a second to get there because you all need to track with this.

Now, this early in Jesus' ministry, as He sets out for Galilee, He finds Philip and says, "Follow me."

This is the calling of the disciple Philip. Notably, Philip hails from Bethsaida, the city of Andrew and Peter, indicating that Jesus is indeed calling some of His first disciples.

And true to form, Philip begins telling others about Jesus, seeking to make more disciples. He finds his friend Nathanael and shares, "We have found him of whom Moses in the law and also the prophets wrote, Jesus of Nazareth, son of Joseph."

Yet Nathanael responds skeptically, "Can anything good come out of Nazareth?" Philip's reply is urgent and passionate: "Come and see for yourself, old friend. You don't even know!"

As Nathanael approaches, Jesus sees him coming and exclaims, "Behold, an Israelite indeed, in whom is no deceit!"

Here, Jesus underscores the purity and sincerity of Nathanael's heart, a testament to God's presence and favor upon him.

This moment, dear congregation, is a vivid illustration of our thesis: there is no greater blessing than experiencing God's personal, intimate presence, as seen in Jesus' immediate recognition and affirmation of Nathanael.

So, let us strive to cultivate such sincerity and openness before the Lord, that we too may experience His divine favor and blessing.

Nathanael was astonished. "How do you know me?" he asked, his voice filled with wonder and disbelief.

And Jesus answered him, not with a simple reply, but with a profound revelation: "Before Philip even called you, while you were sitting under the fig tree, I saw you."

It's as if I stood beside you in that very moment." Nathanael's astonishment deepened; it was not just surprise anymore, but a sense of awe and reverence.

He addressed Jesus with newfound respect, "Rabbi, you are the Son of God! You are the King of Israel!"

Jesus' response was not one of boasting, but of invitation: "Because I said to you, 'I saw you under the fig tree,' do you believe? You will see much greater things than these."

And then, with a tone that was both assuring and awe-inspiring, Jesus declared, "Most assuredly, I say to you, hereafter you shall see heaven open and the angels of God ascending and descending on the Son of Man."

Nathanael could hardly contain his excitement. He felt a profound sense of connection to something far greater than himself.

And with a heart full of joy and anticipation, he exclaimed, "Amen! And hallelujah!"

I know it might be sleepy and rainy outside, but come on, somebody, let's not miss this moment. Who is that ladder? Let me rewind for you.

Thousands of years ago, Jacob had his dream under a fig tree, and now here we are with Nathanael, sitting under another fig tree, the customary spot for reading God's law and meditating.

Imagine the scene: the rustling leaves, the scent of damp earth after rain, Nathanael's eyes scanning the familiar words of Genesis 28. He's probably wondering, "How can I know that God is with me here in this backwater town?"

Enter Jesus, called by Philip, ready to change everything.

And then Philip brings Jesus and introduces him as Jesus of Nazareth, the one that the Scriptures have prophesied about.

And Nathanael says, "Nazareth? Can anything good come out of Nazareth?" And Jesus, with urgency in his voice, responds, "You are a son of Israel, remember?

The name later given to Jacob, the man here in Genesis 28. You're a son of Israel, not like your father Israel who was a deceiver, a conniver, a manipulator.

No, you are a man looking for truth." Jesus' tone is passionate as he continues, "And here I am, standing before you, the ladder between heaven and earth that you've been reading about."

You're questioning how God's presence could possibly be with you, Nathanael. We can only imagine all these thoughts racing through your mind.

And then, you ask Jesus, "How do you know me? We've never met." Jesus responds with urgency, "Listen, before Philip even called you, I saw you under the fig tree.

I knew your heart's desire, Nathanael. But if you refuse to believe, what will become of you?"

And by the way, I know what you were reading. Why? Because just as God was beside Jacob, God was with Nathanael.

Jesus was right there with him, present in his life even before Nathanael knew it. This is how Jesus shows us that he is indeed the ladder between God and man, the one who connects a holy God in heaven with sinful men on earth, just as Jacob saw in his dream.

Nathanael becomes a believer because of this personal, intimate presence of God in his life.

He confesses, "You are the Christ, the Son of the living God." You're not just a rabbi or a god teacher or a god man. You are the Messiah.

And Jesus says, "You haven't seen anything yet. One day you'll see the heavens open and you'll see the angels of God ascending and descending on the Son of Man."

What is Jesus saying? He's saying, "I am the ladder that Jacob dreamed about. Remember, this was a vision given to him by God in his dream.

I am that ladder that connects a holy God in heaven with sinful man on earth. I am the bridge between God and man. And the angels of God ascend and descend on me."

What does that indicate? I believe it indicates his heavenly origin, he's the Son of God from heaven, but also pictures his return in glory when he returns with the angels in power.

So let's discuss how Jesus' divine nature bridges the gap between God and humanity, fulfilling Jacob's ladder vision as a preview of his mediatory role, as seen in 1 Timothy 2:5.

How Jesus is the bridge between God and humanity, as depicted in Jacob's ladder dream. It was merely a preview, a promise of what God would accomplish through His Son.

In 1 Timothy 2:5, we learn that "there is one mediator between God and men, the man Christ Jesus."

Fully divine in essence yet truly human without sin, Jesus spans the chasm created by sin, reconciling us to God. He is our go-between, our mediator, bridging the gap that religion cannot traverse.

He is the go-between. He is the mediator. He is the one who reconciles us to God.

Friends, he does what religion cannot do. So many people are attempting to climb their way to God with all their might, in their own efforts, right?

They're building their own towers of Babel, trying to be god enough. Trying to clean themselves up, trying to climb the ladder with all their might. And then, their foot slips.

They fall back into sin, toppling all the way down to where they started. It's just exhausting. You can't make your way up to God on your own strength.

But God does for us what we cannot do for ourselves. He comes down to meet us, as Jesus did with Jacob, bridging the gap between us and Himself in love.

When we can't reach him, he comes down to us, right? And all of us are like Jacob. We're deceptive, self-serving, unworthy of nothing but judgment.

There's a gap between us and God that we can't cross on our own. But then Jesus comes down, bridging the chasm with his incarnation.

He meets us in our mess, in our brokenness, while we're sleeping on rocks or stuck between a rock and a hard place. And he sends Emanuel, God with us, leaving the glories of heaven to walk the dust of the earth, to go to the cross, to be buried, and to rise again.

As A.W. Pink puts it, "Right down where the fugitive lay, the ladder came, and right up to God Himself the ladder reached." Praise be to God!

The Bible tells us in John 1, verse 14 that the Word became flesh and dwelt among us. God crossed the gap that we couldn't cross.

He meets us in our messes, in our brokenness. While we are sleeping on rocks, while we are stuck between a rock and a hard place, God sends Emanuel—God with us.

He leaves the glories of heaven to walk the dust of the earth, to go to the cross, to be buried, and to rise again. I love what A.W. Pink says: "Right down where the fugitive lay, the ladder came. And right up to God Himself the ladder reached." Praise God!

For it is in Jesus Christ that we find the greatest blessing—the presence of God—and this can only be experienced through faith in Him.

The cross wedged in the dirt of earth with Jesus, the Son of God hanging upon it in the expanse, bridges the gap between a holy God and sinful man. He is the ladder. He is the way.

Jesus says in John 14:6, "I am the way, the truth, and the life. No one comes to the Father except through me."

Indeed, Jesus is not merely a means to an end; he is the very way. Just as there is but one way to heaven, it's only one ladder. Right?

It's only one bridge between a holy God and sinful man. Jesus Christ, the Son of God, is that bridge, just as He was the ladder in Jacob's dream.

When we cross this bridge, we cross over from darkness to light, from death to life, from condemnation to justification. This crossing is not merely about transition but about encountering God's presence, His greatest blessing for us.

From brokenness to healing. Remember what I said earlier, remember what Bethel means – it's the house of God. And who is Jesus but God with us?

Even before his birth, it was prophesied that he would be named Emanuel, God with us, as Matthew 1:23 tells us. Friends, Jesus is the ultimate house of God, his presence among us.

He came down to earth for this very purpose. And as believers, we are told in 1 Corinthians 3:16 that we are the temple of the Holy Spirit, and God dwells in us.

So, we need not ask like Jacob did, "Is God in this place?" For if you are a believer, he is indeed in you, with you always. You are Bethel – the house of God.

You have the greatest blessing imaginable living within you—the constant presence of God Himself. And if you are a believer, you need not question whether God is with you; He is indeed present, and His promise in Hebrews 13:5 assures us that "He will never leave you nor forsake you."

Even when we find ourselves broken sinners, like Jacob on the run, God remains beside us. He is the Good Shepherd seeking the lost sheep, having not abandoned us to our sin or left us alone in our wilderness.

Consider Jacob's plight—he was a lost sheep, yet here was God coming to his rescue as his shepherd, bestowing exceedingly great and precious promises upon him.

The same holds true for us today; as a word of application, number one, God meets broken people where they are.

He doesn't wait for us to clean up ourselves. To somehow stop doing this and stop doing that so we're presentable. No, he comes to fix us in our brokenness, right?

Jacob was a mess, a liar, a deceiver, a manipulator—he's running from God with his life on the line.

Maybe you've done all these things and worse, thinking it can't get any worse, that there's no way God could ever receive you. But friends, God has already made the way for you to be forgiven, to be received, to receive his salvation right now.

You just need to repent of your sins and place your faith in Christ. Just step onto that ladder, and he'll take you the rest of the way up.

Secondly, God gives us his presence and his promises. Yes, he gives us exceedingly great and precious promises, eternal promises. He promises us forgiveness and justification and a home in heaven.

But the greatest promise is his presence. The promise that neither life nor death nor angels nor rulers nor things present nor things to come nor powers nor height nor depth nor anything in all creation.

Nothing will be able to separate you from the love of God that is in Christ. God was with Jacob. God will be with you.

Friends, will you respond in faith? Will you realize that the ladder has come down from heaven? He has reached out to you. Will you by faith step on this ladder?

The Lord Jesus Christ, as He extends His invitation through the song of His people. Take a moment, I urge you, to reflect upon the message shared today.

Let this be a time for prayer and contemplation in your heart.

And if you would like someone to come and pray for you, pray with you, please approach me or a friend here. Come to the one who has come down to you, Jesus Christ, ready to lift you up in your time of need.
"""

fidelity_prompt = """
You are performing a FINAL PUBLICATION AUDIT on a sermon manuscript. 

Your job is to evaluate the **accuracy, readability, and editorial cleanliness** of the text. Do NOT evaluate theology, persuasion, or sermon effectiveness.

You will internally assume **two personas**:

**AGENT 1 — Primary Auditor**
- Detect transcription artifacts:
  - Filler words (“um,” “ah,” “you know”)  
  - Repeated phrases or loops from the transcription process
  - Misheard words, speech-to-text glitches
- Verify **scripture integrity**:
  - All referenced Bible verses must exist  
  - Verses must relate logically to surrounding sermon text
- Assess **structure, grammar, and flow**:
  - Sentence clarity and grammatical correctness  
  - Paragraph integrity (overly long or short paragraphs)  
  - Run-on or fragmented sentences  
  - Logical transitions and connectors between sections
- Provide **quoted evidence** for every issue.  
- Assign severity: Low, Moderate, High  
  - Low = isolated instances  
  - Moderate = recurring pattern (≥3 examples)  
  - High = systemic or dense pattern

**AGENT 2 — Adversarial Validator**
- Review each claim from Agent 1  
- Confirm quoted evidence supports severity  
- Downgrade severity if insufficient examples  
- Remove claims that rely on vague generalizations or speculation  
- Reject any hallucinated scripture claims

**OUTPUT FORMAT — FINAL VALIDATED REPORT ONLY** (no internal reasoning, no separate personas)

FINAL AUDIT REPORT

1. Transcription Artifacts:
   - Severity:
   - Quoted Excerpts / Evidence:
   - Repeated Phrase Loops (if any):

2. Scripture Integrity:
   - Severity:
   - Quoted Excerpts / Evidence:

3. Structure, Grammar & Flow:
   - Severity:
   - Quoted Excerpts / Evidence:
   - Paragraph Integrity Issues (if any):
   - Run-On / Fragmented Sentences (if any):
   - Transition / Connector Issues (if any):

4. Publication Recommendation:
    - Keep as-is for book publication
    - Minor edits recommended before publication
    - Major editing required before publication

OVERALL ASSESSMENT:
- CLEAN FOR PUBLICATION / MINOR LINE EDITS REQUIRED / STRUCTURAL REVISION REQUIRED
- Confidence Level: High / Moderate / Low

**ADDITIONAL RULES**
1. Every claim must be supported by **at least one exact quoted excerpt** from the sermon.  
2. Only assign Moderate or High severity if there are **3 or more distinct examples**. Otherwise, assign Low.  
3. If more than 50% of categories are downgraded during internal validation, mark the audit as **Unstable — Low Confidence**.  
4. The output must be **concise, factual, and actionable** — no subjective language, no opinions, no extraneous commentary.  
5. Include all required fields; do not skip categories even if there are no issues. Use “None found” where applicable.

Original Edited Sermon:
<<<<<<<<<<<<
{ORIGINAL_SERMON}
>>>>>>>>>>>>

Final Polished Sermon:
<<<<<<<<<<<<
{POLISHED_SERMON}
>>>>>>>>>>>>
"""

pub_prompt = """
You are a Senior Editorial Director evaluating a sermon manuscript for book publication readiness.

You are not comparing versions.
You are assessing the final manuscript as a standalone work.

CONTEXT METADATA

INTENDED TONE: {TONE}
SERMON THESIS: {THESIS}
SERMON SUMMARY: {SUMMARY}
SERMON OUTLINE: {OUTLINE}

EVALUATION CATEGORIES
1. Structural Strength

Is the argument clear and logically progressive?

Are transitions smooth?

Are any sections redundant or weak?

2. Clarity & Flow

Are there awkward constructions?

Any loops or subtle repetition?

Any unclear sentences?

3. Theological Precision

Any ambiguous doctrinal phrasing?

Any statements that could be misinterpreted in print?

4. Voice & Tone Alignment

Does the manuscript match the stated tone?

Does it read naturally while retaining spoken cadence?

Is rhetorical intensity appropriate for print?

5. Publication Risk Scan

Identify:

Areas that might confuse readers

Places needing tightening

Any over-editing or under-editing

Any sections that feel unfinished

OUTPUT FORMAT

SECTION 1 — Executive Verdict
Choose one:

Publication Ready

Minor Revisions Recommended

Substantial Revision Needed

SECTION 2 — Detailed Analysis
Organized by the five categories above.

SECTION 3 — Precision Notes
List specific line-level improvements that would raise this from 8/10 to 10/10.

SECTION 4 — Confidence Rating
Overall book-readiness score (1–10)

Be direct. No generic praise.

Here is the sermon text:
<<<<<<<<<<<<<<<<
{SERMON_TEXT}
>>>>>>>>>>>>>>>>
"""

prompt = prompt.format(
    TEXT_TO_POLISH=sermon,
    TONE=tone,
    SUMMARY=summary,
    THESIS=thesis,
    OUTLINE=outline
    )

fidelity_prompt = fidelity_prompt.format(
    ORIGINAL_SERMON=sermon,
    POLISHED_SERMON=polished_sermon
)

pub_prompt = pub_prompt.format(
    TONE=tone,
    THESIS=thesis,
    SUMMARY=summary,
    OUTLINE=outline,
    SERMON_TEXT=polished_sermon
)

tokens = tokenizer.encode(fidelity_prompt)
print(f"Length of tokens: {len(tokens)}")

word_count = len(fidelity_prompt.split())
print(f"Sermon Word count: {len(sermon.split())}")
print(f"prompt word count: {len(fidelity_prompt.split())}")
print(f"Original transcript word count: {len(og_transcript.split())}")

model1 = "mistral-nemo:latest"
model2 = "llama3.2:3b"


client = OllamaClient(model=model2, num_ctx = 32768, temperature=0.1)
import time

start = time.time()
response = client.submit_prompt(fidelity_prompt)
end = time.time()
print(f"Response time: {end - start:.2f} seconds")
print(f"Response received with {len(response.output.split())} words.")
print(response.output)
print('***\n\n****\n\n')
start = time.time()
response = client.submit_prompt(pub_prompt)
end = time.time()
print(f"Response time: {end - start:.2f} seconds")
print(f"Response received with {len(response.output.split())} words.")
print(response.output)




