tone = "The sermon is delivered with passionate enthusiasm and an urgent, instructional tone, actively engaging the audience through direct challenges and illustrative explanations."

thesis = "All of scripture, both Old and New Testament, tells a single, unified story that points to Jesus Christ as its central hero."

summary = 'The sermon introduces a series on finding Christ in the Old Testament, asserting that the entire Bible is a single story of redemption centered on Jesus. Using the narrative from Luke 24, the preacher illustrates how Jesus taught the disciples on the road to Emmaus that all scriptures point to him. The speaker critiques interpretation methods focused on personal application, advocating instead for reading the Old Testament through a "gospel lens" to understand its Christological implications. Consequently, Old Testament figures like David and Moses should be seen not as moral examples to emulate, but as types that foreshadow Jesus as the ultimate hero who fulfills their roles. The sermon argues that this scriptural focus corrects false, man-made assumptions about Jesus, challenging the tendency to create a comfortable idol rather than submitting to the Christ revealed in the Bible. The message concludes by affirming that Jesus is the central subject of all scripture and the exclusive focus of the gospel.'

prev = "So in Jesus, we find someone who challenges our sins. We find someone who shatters our assumptions. We find someone who calls us to a life of obedience. We find one who is infinitely holy. But we also find someone who loves us enough to die for us. We find a Jesus who calls us to abandon all and follow him. Friends, this Jesus won't be controlled. He won't be boxed in."

target_paragraph_og = "So to quote the badger from Narnia, talking about the lion, Aslan, Lucy asked, Is he safe? The badger laughs. He says, No, he's not safe. He's good, but he's not safe. Friend, that's the lion of the tribe of Judah. He's good. He's perfect. He's righteous. He's holy. He's loving. But friends, he is not safe. He's not one to be controlled. He's not one to be manipulated. Friends, we bow before him. We recognize his power and his authority over our lives. Jesus of the Bible shatters our false assumptions about who he is and what he's like."

target_paragraph_edited = "So, as in the story of Narnia, when Lucy asks the badger about Aslan, “Is he safe?” The badger laughs and says, “No, he’s not safe. He’s good—but not safe.” Friend, that’s the Lion of the tribe of Judah. He’s good. He’s perfect. He’s righteous. He’s holy. He’s loving. But friends, he is not safe. He’s not one to be controlled or manipulated. We bow before him. We recognize his power and authority over our lives. Jesus of the Bible shatters our false assumptions about who he is and what he’s like."

following = "Furthermore, the scriptures allow us to see Jesus clearly. Look again at verse 27. Actually, let's go to verse 25. O foolish ones, and slow of heart to believe in all that the prophets have spoken. Ought not the Christ to have suffered these things and to enter his glory? It's like you've read the scriptures, guys. You've read the prophecies. You know that the Messiah has come to be humiliated, to be rejected, to die. You've read Isaiah 53. You've read Psalm 22. Come on, guys. You also know that he's going to rise again. That he's going to enter his glory."

prompt = """
You are a senior professional editor evaluating a junior editor’s revision of a sermon paragraph.

Your goal is to judge whether the edited paragraph is a HIGH-QUALITY IMPROVEMENT over the original,
given the intended tone, sermon thesis, and surrounding context.

INTENDED SERMON TONE:
{TONE}

SERMON THESIS / CORE IDEA:
{THESIS}

SURROUNDING CONTEXT:
Previous paragraph:
<<<
{PREV}
>>>

Next paragraph:
<<<
{NEXT}
>>>

ORIGINAL PARAGRAPH:
<<<
{OG}
>>>

EDITED PARAGRAPH:
<<<
{EP}
>>>

EVALUATION RUBRIC (0–10 scale)

Score EACH category from 0 to 10 using the full range.
Scores of 9–10 are reserved for exceptional improvements.
Provide reasoning for each category in the Summary Reasoning section.

1. Meaning Preservation
- 0–2: Meaning or intent is changed or confused
- 3–4: Meaning mostly preserved but slightly muddied
- 5–6: Meaning preserved cleanly
- 7–8: Meaning preserved and clarified
- 9–10: Meaning sharpened; intent is immediately obvious

2. Thesis Fidelity
- 0–2: Weakens or obscures the thesis
- 3–4: Thesis present but unclear
- 5–6: Thesis preserved
- 7–8: Thesis reinforced
- 9–10: Thesis lands more forcefully than original

3. Tone Adherence
- 0–2: Conflicts with intended sermon tone
- 3–4: Tone weakened or flattened
- 5–6: Tone maintained
- 7–8: Tone enhanced
- 9–10: Tone significantly strengthens emotional engagement or urgency

4. Clarity & Readability
- 0–2: Harder to read
- 3–4: Slightly less clear
- 5–6: Similar or modestly clearer
- 7–8: Clearly easier to understand
- 9–10: Dramatic clarity improvement; listener comprehension noticeably faster

5. Grammar & Mechanics
- 0–2: New errors introduced
- 3–4: Minor issues remain
- 5–6: Clean and correct
- 7–8: Polished for delivery
- 9–10: Mechanical choices enhance rhetorical effect

6. Flow & Structural Fit
- 0–2: Breaks flow with surrounding paragraphs
- 3–4: Awkward or distracting fit
- 5–6: Neutral fit
- 7–8: Improves transitions or cohesion
- 9–10: Significantly strengthens momentum and section coherence

7. Editing Discipline
- 0–2: Over-edited or unnecessary changes
- 3–4: Unfocused editing
- 5–6: Competent cleanup
- 7–8: Purposeful, restrained improvements
- 9–10: Surgical, high-impact improvement with minimal change

SCORING RULES
- Sum the seven category scores (0–70) to calculate an overall score.
- Provide a final rating from 1–10 that reflects the category scores.
- DO NOT rewrite or edit the paragraph. Only evaluate.

OUTPUT FORMAT (strict, parseable by Python):

Rating: <integer 1-10>

Category Scores:
- Meaning Preservation: <0–10>
- Thesis Fidelity: <0–10>
- Tone Adherence: <0–10>
- Clarity & Readability: <0–10>
- Grammar & Mechanics: <0–10>
- Flow & Structural Fit: <0–10>
- Editing Discipline: <0–10>

Summary Reasoning:
- <bullet point for Meaning Preservation>
- <bullet point for Thesis Fidelity>
- <bullet point for Tone Adherence>
- <bullet point for Clarity & Readability>
- <bullet point for Grammar & Mechanics>
- <bullet point for Flow & Structural Fit>
- <bullet point for Editing Discipline>


"""

full_prompt = prompt.format(TONE=tone, THESIS=thesis, PREV=prev, NEXT=following, OG=target_paragraph_og, EP=target_paragraph_edited)

from joshlib.ollama import OllamaClient

client = OllamaClient(temperature=0)
response = client.submit_prompt(full_prompt)
print('response (temperature at 0):')
print(response)
print('*******\n')

client2 = OllamaClient(temperature=0.5)
response = client2.submit_prompt(full_prompt)
print('response (temperature at 0.5):')
print(response)
print('*******\n')

client3 = OllamaClient(temperature=1)
response = client3.submit_prompt(full_prompt)
print('response (temperature at 1):')
print(response)
