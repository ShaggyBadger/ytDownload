import re
import sys

def parse_evaluator_output(output):
    # Extract the integer Rating
    rating_match = re.search(r"Rating:\s*(\d+)", output)
    rating = int(rating_match.group(1)) if rating_match else 0
    
    # Extract the Critique specifically between the triple brackets
    critique_match = re.search(r"CRITIQUE FOR REDO:\s*<<<\s*(.*?)\s*>>>", output, re.DOTALL)
    critique = critique_match.group(1).strip() if critique_match else "No feedback provided."
    
    return rating, critique

tone = "The sermon is delivered with passionate enthusiasm and an urgent, instructional tone, actively engaging the audience through direct challenges and illustrative explanations."

thesis = "All of scripture, both Old and New Testament, tells a single, unified story that points to Jesus Christ as its central hero."

summary = 'The sermon introduces a series on finding Christ in the Old Testament, asserting that the entire Bible is a single story of redemption centered on Jesus. Using the narrative from Luke 24, the preacher illustrates how Jesus taught the disciples on the road to Emmaus that all scriptures point to him. The speaker critiques interpretation methods focused on personal application, advocating instead for reading the Old Testament through a "gospel lens" to understand its Christological implications. Consequently, Old Testament figures like David and Moses should be seen not as moral examples to emulate, but as types that foreshadow Jesus as the ultimate hero who fulfills their roles. The sermon argues that this scriptural focus corrects false, man-made assumptions about Jesus, challenging the tendency to create a comfortable idol rather than submitting to the Christ revealed in the Bible. The message concludes by affirming that Jesus is the central subject of all scripture and the exclusive focus of the gospel.'

prev = "Sometimes we struggle to make sense of the genealogies—the begats and the begotten, this one begat that one, and that one begat that one—and then we lose focus when it goes into the sacrifices and the strange customs of Leviticus. However, some see it simply as a historical narrative of the nation of Israel that has little or no application to the church today, still over the years. Others interpret the Old Testament merely as moral lessons or examples for us to follow, and you hear that in preaching a lot today."

target_paragraph_og = "But let me propose to you today that most people are guilty of practicing the form of biblical interpretation called reader response hermeneutics reader response hermeneutics hermeneutics is simply the method of interpreting the bible and we're all guilty of it whether we are familiar with that phrase or not reader response hermeneutics and this is when we ask what does this mean to me you ever ask that when you're reading the bible well what does this mean to me or you go to a bible study and there's no clear exposition of the text it's just well what does this mean to you somebody will give an answer what's this mean to you somebody gives a completely different answer well what's this mean to me we got 10 people we got 10 different people we got 10 different people we got 10 different answers."

target_paragraph_edited = """But let me propose to you today that most people are guilty of practicing the form of biblical interpretation called reader response hermeneutics. Reader response hermeneutics is simply the method of interpreting the Bible, and we're all guilty of it, whether we know the term or not. Reader response hermeneutics is when we ask, "What does this mean to me?" Have you ever asked that when reading the Bible? Well, what does this mean to me? When we go to a Bible study and there's no clear exposition of the text, it's just, "Well, what does this mean to you?" Someone gives an answer. "What does this mean to you?" Someone else gives a completely different answer. "What does this mean to me?" We have 10 people—we have 10 different answers."""

following = "That's not how to interpret the Bible. There's only one clear interpretation, and we let the Bible interpret itself. We don't read our meaning into the text—we derive our meaning from the text. So, how do we do that? We come to the Bible and ask a series of questions. We have to ask: who wrote the book—understanding the author provides insight into the perspective and purpose of the writing. Who wrote the book? Who was it written to? We must know the audience, and that helps us grasp the culture and the spiritual context of the book. If we're studying a passage, we need to understand its context. We don't just take a verse in isolation—we understand the surrounding chapters and the broader themes of the book itself. Because guess what: I can take one verse and make it mean anything I want it to mean. I've twisted it. Instead, I take the whole book. What is God communicating with me? What is the author's intention? Who was it written to? And we also ask: what's the literal, grammatical, and historical setting? What does the original language say? What's the historical background? What is going on in this passage? What literary style is the author employing—this gives clarity to the passage's meaning."

prompt = """
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

revision_prompt = """
You are an expert Sermon Editor. Your task is to polish the TARGET PARAGRAPH for maximum impact and clarity.

### CONTEXT
- **THESIS:** {THESIS}
- **TONE:** {TONE}
- **FLOW:** [Prev: {PREV}] -> [Next: {NEXT}]

### FEEDBACK FROM PREVIOUS VERSION
If the section below contains a critique, you MUST prioritize addressing these specific points in your new edit.
<<<
{CRITIQUE}
>>>

### EDITING RULES
1. **Theological Shield:** Do not change the underlying meaning or scripture references.
2. **Rhetorical Pulse:** Keep the "spoken" feel. Do not remove repeated words if they provide emotional weight.
3. **Discipline:** Only fix what is clunky or confusing. If it isn't broken, don't "over-write" it.

TARGET PARAGRAPH:
<<<
{OG}
>>>

REVISED PARAGRAPH:
(Provide ONLY the revised text. No preamble or explanation.)
"""

full_prompt = prompt.format(TONE=tone, THESIS=thesis, PREV=prev, NEXT=following, OG=target_paragraph_og, EP=target_paragraph_edited)

from joshlib.ollama import OllamaClient

client = OllamaClient(temperature=0.1)
response = client.submit_prompt(full_prompt)
print('response...')
print(response)
print('\n\n******\nRunning revision....')

rating, critique = parse_evaluator_output(response)
print(f'Rating: {rating}')
print(f'Critique: {critique}')
if "none" in critique.lower():
    print('Ending program: No critique to process.')
    sys.exit()
print('******\n\n')

full_revision_prompt = revision_prompt.format(
    THESIS=thesis,
    TONE=tone,
    PREV=prev,
    NEXT=following,
    CRITIQUE=critique,
    OG=target_paragraph_og
)

editor_client = OllamaClient(temperature=0.7)
response = editor_client.submit_prompt(full_revision_prompt)
print(response)



