def condense_text(input_text):
    # .split() without arguments splits by any whitespace 
    # and discards empty strings caused by extra spaces/newlines.
    words = input_text.split()
    
    # Rejoin the words with a single space
    return " ".join(words)

# Example usage:
raw_text = """
The New Testament bears witness to them. It is written of Him that He went about doing good, such good, such wonderful good, such extraordinary good, good that none else had ever been able to do.

- Think of the honey sweet words of counsel, of comfort, of conviction, of courage that fell from His lips!
- Think of the mighty miracles of His healing!
- Think of His unstopping the mouths of the dumb, opening the eyes of the blind, the ears of the deaf!
- Think of Him stopping and, as someone has said, breaking up every funeral He attended!

Surely the people of His day and time should have fallen at His feet, if for no other reason than because of His works, and cried out, as one did say, "Thou art the Christ, the Son of the living God."

Think further of the testimony not only of the New Testament but of history, of secular, non-religious history.

Listen! I come from a city in Russia named Maghiliev. It is on the Dnieper River. At the time I lived there, it had a population of between 150,000 to 200,000. That was just before 1914. The entire city of more than 150,000 people had one small hospital, one drug stare, two doctors, one assistant doctor. There were four schools - two grade schools, one high school, one junior college. In all the four schools there were not a thousand, certainly not fifteen hundred students. n all the four schools there were not one hundred girls. The majority of the students were boys. Girls were not supposed to get an education.

What was the difference between Russia and the Chicago to which I came? What is the difference between Moghiliev and any city of the United States? People have two feet in Russia, two hands, two eyes, two ears, one nose. They take baths. They sleep. They are married and given in marriage. When you prick them, they bleed. When you poison them, they die. When you hurt them, they weep. What is the difference between Russia and America? I shall tell you.

In America the Lord JESUS CHRIST has been given a chance. In Russia He had not been up to that time, and of course He is not being given a chance now. I read of a Mohammedan preacher, a follower of Mohammed who had become a Christian. He said that in his country, in Turkey, if he had a choice between being a woman or a donkey, he would be a donkey, because his master would take better care of him than any husband took of his wife.

You dear sisters who are reading this, why are you not in some purdah of the Arabians, of the Turks, of the Hindus? Why are you not circumscribed in your activities? Why can you associate with others, going here, there, and yonder, just as openly as the men? Why do you not wear the veil? What is the difference? Is a Mohammedan woman ugly? Not at all. Is she indecent? Not all. Do they have something so terribly wrong with them, something not found in American women? Of course not. It is simply because you American women have your lives built in the foundation of the Blood of the Lord JESUS CHRIST.

Listen, my friends. When the Anglos and the Saxons were eating each other in the forests of Germany, in cannibalistic orgies, the Chinese were already writing, printing, dressing in silks and satins. Compare England with China today. China, backward, poor China, benighted, forlorn! England, a paragon among the nations!
What made England? Was it its Shakespeares? Perish the thought! Was it its Miltons? Forget it! What made England? Was it its factories? What made England? Was it its dances, its armies, its navies? No!

Definitely, truly, wholly, entirely, it is the CHRIST of the living GOD! The Gospel was preached in that country while poor China did not have the same chance. May I digress a moment? Far as long as the world stands, England and America, especially America, will never cease paying for the fact that we had the opportunity at China and missed it. China will be a sword at our hearts, a dagger at our throats because of its being taken over by the communists instead of by the Lord JESUS CHRIST.

It is the same everywhere you turn. No one who has ever read that matchless story of Queen Victoria can ever forget it. One of her Zulu king subjects came with his mighty retinue from his kraal yonder in Africa to visit her. Taking him into her carriage, as one of her great subjects, she rode him around the city of London to show him the sights of that mighty metropolis. Returning to her palace, she sat down on her throne. The giant Zulu, the black warrior, stood in front of her, leaning on his terrible spear as he spake:

"White Mother, I shall never dare tell my people what you have showed me this day. They will not believe me! They would kill me for a liar. But, I want to ask you a question that has been bothering me all this day. My people are bigger than your people. My people are as numerous as your people. My people are as strong as your people. I can take any two of your soldiers and break them with these two hands. There is not a man in your kingdom that I have seen that would be a physical match for one of my warriors. Why is it that you are so great and we are so small?"

You recall the answer. GOD bless the memory of that saintly queen! Stepping down from the throne, taking her Bible from a table by the side of the dais, lifting it before the king, she said: "King, this is the secret of the greatness of my empire!" Oh, how I wish someone would tell that to the President of the United States, to the Cabinet in Washington! They all need to know that. They seem to have forgotten this lesson, this testimony of history.
"""

clean_paragraph = condense_text(raw_text)
print(clean_paragraph)