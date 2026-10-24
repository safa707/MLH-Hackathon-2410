define p = Character("[player_name]", who_color = "#850c83", what_color ="#5250d4", what_prefix="\"", what_suffix="\"")
define s = Character("Gemma", who_color = "#7272f2", what_color = "#7272f2", what_prefix="\"", what_suffix="\"") 
define c = Character("Phone", who_color = "#0e4155", what_color = "#4faa92", what_prefix="\"", what_suffix="\"")

define ai_result = {"done": False, "text": ""}

image s neutral = "gemmaneutral"
image s nervous = "gemmanervous"
image s angry   = "gemmaangry"
image s scared  = "gemmascared"
image s smug    = "gemmasmug"
image bg interrogation = "interrogationroom"

define config.default_music_volume = 0.1
define config.default_sfx_volume = 0.1

init python:
    import json
    import urllib.request as urllib2
    import ssl
    import time
    import string
    allowChars = string.ascii_letters + string.digits + " " + "'"

    GEMINI_API_KEY = "KEY HERE"
    
    def ask_gemma_ai(player_input):
        system_instruction = (
            "You are playing a role in a detective game. Your name is Gemma. "
            "You work as a cleaner in this house."
            "You are a nervous thief being interrogated for stealing. "
            "CRITICAL RULES:\n"
            "1. Stay in character at all times. Never mention you are an AI.\n"
            "2. Keep your answers brief (strictly 1 to 3 short sentences max).\n"
            "3. You hid the diamond under the sink.\n"
            "4. Stress when the kitchen gets mentioned."
            "4. Do not admit to the crime unless the player explicitly mentions 'the sink'."
        )

        model = "gemma-4-26b-a4b-it"
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"

        attempts = [
            {"tokens": 1000, "use_system": True},
            {"tokens": 1000, "use_system": True},
            {"tokens": 600, "use_system": False},
            {"tokens": 600, "use_system": False},
        ]
        errors = []
        t0 = time.time()

        for cfg in attempts:
            if cfg["use_system"]:
                data = {
                    "contents": [{"parts": [{"text": player_input}]}],
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "generationConfig": {"maxOutputTokens": cfg["tokens"]}
                }
            else:
                full_prompt = system_instruction + "\n\nThe detective says: " + player_input + "\n\nGemma replies:"
                data = {
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"maxOutputTokens": cfg["tokens"]}
                }

            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                json_bytes = json.dumps(data).encode('utf-8')
                req = urllib2.Request(url, json_bytes)
                req.add_header('Content-Type', 'application/json')
                req.add_header('x-goog-api-key', GEMINI_API_KEY)

                response = urllib2.urlopen(req, timeout=60, context=ctx)
                raw_json = json.loads(response.read())

                cand = raw_json['candidates'][0]
                parts = cand.get('content', {}).get('parts', [])
                texts = [p['text'] for p in parts if 'text' in p and not p.get('thought')]
                if not texts:
                    texts = [p['text'] for p in parts if 'text' in p]
                answer = " ".join(texts).strip()
                if answer:
                    return answer
                errors.append("empty, finish=" + str(cand.get('finishReason')))

            except urllib2.HTTPError as e:
                body = e.read().decode("utf-8", "ignore").replace("\n", " ")
                errors.append("HTTP " + str(e.code) + " " + body[:70])
            except Exception as e:
                errors.append(str(e)[:60])

            time.sleep(1)

        return "Gemma stays silent. (Failed after %.1fs. %s)" % (time.time() - t0, " | ".join(errors[-2:]))

    def _ai_worker(q):
        ai_result["text"] = ask_gemma_ai(q)
        ai_result["done"] = True

    def start_ai(q):
        ai_result["done"] = False
        ai_result["text"] = ""
        renpy.invoke_in_thread(_ai_worker, q)

    def split_mood(text):
        moods = ["neutral", "nervous", "angry", "scared", "smug"]
        m = re.match(r"\s*MOOD:\s*(\w+)\s*(.*)", text, re.S | re.I)
        if m:
            mood = m.group(1).lower()
            if mood not in moods:
                mood = "neutral"
            return mood, m.group(2).strip()
        return "neutral", text.strip()

label start:

    $ questions_asked = 0
    $ max_questions = 12

    scene black
    $ player_name = renpy.input("What is your name?", default="Detective ")
    $ player_name = player_name.strip() or "Detective"

    "Ringing from the office phone fills the room."
    c "Hey [player_name]! I'm bringing in the suspect for your case. Make sure you're ready to get the truth out of them."
    c "She was their cleaner so she knows a lot about the building."
    "[player_name], ask questions to get Gemma to hint at the evidence. e.g Where they were at the time, their alibi, which room were they in"
    "The lawyers on their way. Make sure to ask good questions!"

    
    scene bg interrogation
    show s neutral

label interrogation_loop:
    with fade

    if questions_asked >= max_questions:
        jump suspect_shuts_down

    menu:
        "Demand Answers (Ask Gemma a question)":
            pass
        "End the Interrogation":
            jump suspect_shuts_down

    
    $ player_question = renpy.input("Type your question to interrogate Gemma:")
    $ player_question = player_question.strip()

    if not player_question:
        jump interrogation_loop

    p "[player_question]"
    $ questions_asked += 1

    "Gemma hesitates, staring at her hands..."
    $ start_ai(player_question)
    while not ai_result["done"]:
        $ renpy.pause(0.2)
    $ ai_response = ai_result["text"].replace("[", "[[").replace("{", "{{")

    # Safe text box string formatting output delivery
    s "[ai_response]"

    # Win-State Verification Check
    if "sink" in ai_response.lower() or "kitchen sink" in player_question.lower():
        jump player_wins_game

    # Render a safe pacing narration box to give the engine time to rest
    $ remaining = max_questions - questions_asked
    "Gemma looks away. You have [remaining] questions remaining before her lawyer arrives."

    jump interrogation_loop



label suspect_shuts_down:
    s "Look, I've had enough of this questioning.."
    s "My lawyer will be here soon. I refuse to say any more."
    "Gemma turns away to look at her phone."
    " "
    "Game Over: You failed to crack her alibi before time ran out."
    return

label player_wins_game:
    "Gemma pales instantly, realizing she just blew her cover."
    s "Wait! No! I didn't mean to..."
    s "You tricked me!"
    " "
    "Success! You found where she hid the diamond!"
    return
