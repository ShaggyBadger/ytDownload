from joshlib.ollama import OllamaClient

tone = """
The sermon is delivered with an earnest and didactic tone, blending cautionary warnings about sin with passionate encouragement and hopeful proclamations of God's grace and redemption.
"""

thesis = """
The Bible reveals that even its greatest heroes are flawed sinners, demonstrating humanity's universal need for a perfect Savior.
"""

prev_para = """
Now this prophecy is threefold. Number one, the curse on Canaan. And we can note enslavement. In addition to this, he says, \"Cursed be Canaan. A servant of servants shall he be to his brethren.\" So let's unpack this. The very first question that arises here is why this curse is placed on Canaan and not Ham. Was it not Ham who went into his father's tent to visit the curse upon his son? First, it's a biblical principle that the sins of the father are visited upon the children to the third and fourth generations. Exodus 20, verse 5. Now we can call this the principle of generational consequence. Now I do not believe in generational curses. Everyone answers for their own sins. Everyone is responsible for their own life. And we will stand before God. But it's also true that children are often shaped by the influence of their parents. For good or for evil. And no doubt Canaan learned a great deal of wickedness from his father Ham. And many times we see this still today. The sins of the parents are reflected in the lives of the children. So if a child grows up in a home of fighting and profanity and drunkenness and indecent behavior, guess what that child is going to grow up and do most likely. He thinks that's normal\u2014that's the only life he's ever known. And he'll create another broken home. The good news of the gospel is that God redeems broken families, broken hearts, and broken homes. And he can write a new story for you. He redeems.
"""

next_para = """
Now, before we think, God, this is unfair. No, God gave them over 400 years to repent while Israel was slaves in Egypt. They failed to. Instead, you know what they did? They practiced child sacrifice. They burned babies in the fire. They worshipped idols such as Molech. They were idolatrous. They were violent. They were wicked people. So, God calls Israel to drive the Canaanites out of their land. Do not marry their sons or daughters. Do not live with them. Do not have business deals with them. Totally drive them out. Why? Because if you let them live in your land, you will learn their practices and they will bring you into idolatry too. Guess what happens? They fail to drive them out. Guess what happens? They fall into idolatry and wickedness. And hundreds of years later, they go into captivity again, this time by the Babylonians. That's what happens when we fail to drive out sin in our lives. That's what happens when we only go halfway in obedience. That's what happens when we play around and flirt around with sin. He is to subjugate Canaan. He is to be a servant of servants to his brethren. But this is also a prophecy about the spiritual war. God is declaring war on the seed of the serpent. God is not just cursing the serpent. He is not just cursing the people or a tribe. He is continuing his plan to crush the serpent's head through the seed of the woman, through the line of Shem, Noah's other son. Because Noah's son, Shem, will have Abraham a few generations later. And it's through Abraham that Israel will come. And it is through Israel that the Messiah, Jesus Christ, will come. We see the blessing upon Shem. And you can write enrichment upon this. And he says, Blessed be the Lord, the God of Shem, and may Canaan be his servant. This next prophecy is for the Shemites, the Semitic people from whom come the Hebrews.
"""

og = """
Second. It's true that children often suffer. For the misdeeds of their parents. Friends we do not sin in a vacuum. Our behavior affects everyone. Especially our children. If I sin. Guess what. My sin affects my wife and my children. Because I'm the leader of my home. If I sin. My sin affects this church. As the elder of this church. We do not sin in a vacuum. But that's the lesson about sin. The pages and \u0440\u0443\u043a of sin. We use Torah. We use faith. Our family. And religion. Which is our creation. We use Money. Then we use interest. We've been falling short. Of a prosperity. No shame. No\u3086 immorality. And no sin. history. Some theologians during that day, during the antebellum era, wrongly claimed that the curse on Canaan or him meant that Africans were cursed. And they said, that's the reason why we can own slaves. Let me tell you, that's a lie straight out of the pit of hell. That is not what this means at all. The children of Canaan are not just Africans, but they're the people of the Near East, such as the Egyptians, such as the Palestinians, such as people who settled in Libya and Sudan. And many of Ham's descendants, like Nimrod, went on to build mighty empires, including Assyria and Babylon and Egypt. This is not talking about African slavery, friends. This is talking about the major enemies of God's people throughout the pages of Scripture. And these nations that descend from the city of Canaan, they are the people of the Near East. And they are the people of the Middle East. And they are the people of the Middle East. And they are the people of the Middle East. The sons of Ham are eventually subjugated by the descendants of Noah's other son, Shem. For example, the Canaanite tribe of the Gibeonites. They're made to serve under Joshua. Later, King Solomon's reign, the Canaanite groups were subjected to forced labor and taxation. The Egyptians are judged by God. He lets his people go. And God ultimately uses the Persians to destroy the Canaanites. And they are known as the Canaanites. Where do we encounter the Canaanites in Scripture? The book of Joshua and the book of Judges, right? They're the ones who are living in the promised land. And the Israelites are to go and drive them out. So, picture yourself in their sandals. You're hearing Moses read this for the first time. You're about to go inherit the promised land. You need justification for driving these wicked Canaanites out. And this is it. They're going to be your slaves. This does not mean that you're going to be your slaves. You're going to be your slaves. You're going to be your household slaves. This means you're going to subjugate them. You're going to conquer them. You're going to rule over them. In fact, their mandate was to drive them out
"""

ep = """
Second. It's true that children often suffer for the misdeeds of their parents. Friends, we do not sin in a vacuum. Our behavior affects everyone, especially our children. If I sin, guess what. My sin affects my wife and my children. Because I'm the leader of my home. If I sin, my sin affects this church. As the elder of this church. We do not sin in a vacuum. But that's the lesson about sin. The pages and pages of sin. We use Torah. We use faith. Our family. And religion, which is our creation. We use money. Then we use interest. We've been falling short of a prosperity. No shame. No immorality. And no sin. Some theologians during that day, during the antebellum era, wrongly claimed that the curse on Canaan meant that Africans were cursed. And they said that's the reason why we can own slaves. Let me tell you, that's a lie straight out of the pit of hell. That is not what this means at all. The children of Canaan are not just Africans, but they're the people of the Near East, such as the Egyptians, such as the Palestinians, such as people who settled in Libya and Sudan. And many of Ham's descendants, like Nimrod, went on to build mighty empires, including Assyria and Babylon and Egypt. This is not talking about African slavery, friends. This is talking about the major enemies of God's people throughout the pages of Scripture. And these nations that descend from the city of Canaan are the people of the Near East. And they are the people of the Middle East. The sons of Ham are eventually subjugated by the descendants of Noah's other son, Shem. For example, the Canaanite tribe of the Gibeonites. They're made to serve under Joshua. Later, King Solomon's reign, the Canaanite groups were subjected to forced labor and taxation. The Egyptians are judged by God. He lets his people go. And God ultimately uses the Persians to destroy the Canaanites. And they are known as the Canaanites. Where do we encounter the Canaanites in Scripture? The book of Joshua and the book of Judges, right? They're the ones who are living in the promised land. And the Israelites are to go and drive them out. So, picture yourself in their sandals. You're hearing Moses read this for the first time. You're about to go inherit the promised land. You need justification for driving these wicked Canaanites out. And this is it. They're going to be your slaves. This does not mean that you're going to be their slaves. You're going to be their household slaves. This means you're going to subjugate them. You're going to conquer them. You're going to rule over them. In fact, their mandate was to drive them out.
"""

evaluation_prompt = """
You are a Senior Editorial Director specializing in homiletics. You are evaluating a junior editor’s revision of a sermon paragraph.

### EVALUATION CONTEXT
- INTENDED TONE: {TONE}
- SERMON THESIS: {THESIS}

### SURROUNDING CONTEXT
- PREVIOUS PARAGRAPH: <<< {PREV} >>>
- NEXT PARAGRAPH: <<< {NEXT} >>>

### CONTENT FOR EVALUATION
- ORIGINAL PARAGRAPH: <<< {OG} >>>
- EDITED PARAGRAPH: <<< {EP} >>>

---

### INSTRUCTIONS
1. Evaluate the edited paragraph strictly in comparison to the original.
2. Assess whether the edit preserves meaning, aligns with the sermon thesis, maintains the intended tone, and improves clarity, grammar, flow, and discipline.
3. Use a 0–10 scale for all categories:
   - 0 = fails completely
   - 5 = neutral / no improvement
   - 10 = perfect improvement or flawless preservation
4. Only output the following EXACTLY. No extra commentary, no explanations outside of the required fields. Ensure all category names match exactly.

### OUTPUT FORMAT

Rating: <integer 1–10>

Category Scores:
Meaning Preservation: <0–10>
Thesis Fidelity: <0–10>
Tone Adherence: <0–10>
Clarity & Readability: <0–10>
Grammar & Mechanics: <0–10>
Flow & Structural Fit: <0–10>
Editing Discipline: <0–10>

Summary Reasoning:
- Meaning Preservation: <reasoning>
- Thesis Fidelity: <reasoning>
- Tone Adherence: <reasoning>
- Clarity & Readability: <reasoning>
- Grammar & Mechanics: <reasoning>
- Flow & Structural Fit: <reasoning>
- Editing Discipline: <reasoning>

CRITIQUE FOR REDO:
<<<
(If Rating is < 8, provide 2-3 specific, actionable instructions to fix the paragraph. If Rating is 9-10, write "None.")
>>>
"""

full_prompt = evaluation_prompt.format(
    TONE=tone, THESIS=thesis, PREV=prev_para, NEXT=next_para, OG=og, EP=ep
)

client = OllamaClient(model="llama3.2:3b", temperature=0.2)
response = client.submit_prompt(full_prompt)
print(response)
