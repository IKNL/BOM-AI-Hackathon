import boto3
import json
import re
import os

client = boto3.client("bedrock-runtime", region_name="us-east-1")
model_id = "openai.gpt-oss-120b-1:0"

# Load cancer type mapping
def load_cancer_mapping():
    """Parse mapping.md to extract cancer types and their markdown files"""
    mapping = {}
    with open("mapping.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract cancer types and their files
    pattern = r'## (.+?)\n\*\*Markdown:\*\* \[`(.+?)`\]'
    matches = re.findall(pattern, content)
    
    for cancer_type, md_file in matches:
        mapping[cancer_type.lower()] = md_file
    
    return mapping

def load_markdown_content(md_file):
    """Load content from a markdown file"""
    try:
        # Ensure we use the correct path
        if not md_file.startswith('data/markdowns/'):
            md_file = f"data/markdowns/{md_file}"
        with open(md_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None

def chunk_markdown_by_sections(content):
    """Split markdown content into sections based on ## headers"""
    sections = []
    current_section = ""
    
    for line in content.split('\n'):
        if line.startswith('## ') and current_section:
            sections.append(current_section.strip())
            current_section = line + '\n'
        else:
            current_section += line + '\n'
    
    if current_section:
        sections.append(current_section.strip())
    
    return sections

def find_relevant_sections(user_prompt, sections, max_sections=5):
    """Find most relevant sections based on keyword matching"""
    keywords = user_prompt.lower().split()
    scored_sections = []
    
    for section in sections:
        score = sum(1 for keyword in keywords if keyword in section.lower())
        scored_sections.append((score, section))
    
    # Sort by score and take top sections
    scored_sections.sort(reverse=True, key=lambda x: x[0])
    return [section for score, section in scored_sections[:max_sections]]

def find_best_match(user_input, cancer_mapping):
    """Find the best matching cancer type from user input"""
    user_input_lower = user_input.lower()
    
    # Direct match
    if user_input_lower in cancer_mapping:
        return user_input_lower
    
    # Partial match
    for cancer_type in cancer_mapping.keys():
        if cancer_type in user_input_lower or user_input_lower in cancer_type:
            return cancer_type
    
    return None

def onboarding_query(prompt: str, user_context: dict) -> dict:
    """Query LLM for dynamic onboarding conversation"""
    context_str = json.dumps(user_context, indent=2)
    
    system_prompt = f"""You are conducting a brief onboarding for a cancer information assistant.

You must gather exactly 4 pieces of information in this STRICT order:

Step 1: If 'wellbeing' is NOT in context → store their response as wellbeing and ask: "Wat is uw leeftijd en geslacht?"
Step 2: If 'age' or 'gender' is NOT in context → extract age and gender from response, then ask: "Hoe gedetailleerd wilt u de informatie? (eenvoudig, gedetailleerd, of wetenschappelijk)"
Step 3: If 'answer_style' is NOT in context → store their preference and ask: "Over welk type kanker wilt u informatie?"
Step 4: If 'cancer_type' is NOT in context → extract cancer type and set onboarding_complete to true

Current context:
{context_str}

CRITICAL RULES:
- ALWAYS move to the next question after storing the current answer
- Do NOT ask follow-up questions
- Do NOT repeat the same question
- Extract information from user's response even if brief
- If user says "ok", "goed", "niet goed" etc → store as wellbeing and move to next question

Return JSON:
{{
  "response": "next question in Dutch",
  "context_update": {{"key": "value"}},
  "onboarding_complete": false
}}

User message: {prompt}

Your response (JSON only):"""
    
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "messages": [{"role": "user", "content": system_prompt}],
            "max_tokens": 512,
            "temperature": 0.3
        })
    )
    result = json.loads(response['body'].read())
    raw_content = result['choices'][0]['message']['content']
    
    if '<reasoning>' in raw_content:
        raw_content = raw_content.split('</reasoning>')[-1].strip()
    
    return json.loads(raw_content)

def onboarding():
    """Conduct dynamic onboarding conversation"""
    print("\n" + "=" * 60)
    print("Welkom bij de Kanker Informatie Assistent")
    print("=" * 60)
    print("\nOver welk type kanker wilt u informatie?")
    print("(U kunt ook 'skip' typen om over te slaan)\n")
    
    user_context = {}
    last_user_input = None
    
    while True:
        user_input = input("U: ").strip()
        last_user_input = user_input
        
        if user_input.lower() == 'skip':
            return None, None
        
        try:
            result = onboarding_query(user_input, user_context)
            
            # Update context
            if result.get('context_update'):
                user_context.update(result['context_update'])
            
            # Check if complete (cancer type identified)
            if result.get('onboarding_complete') and user_context.get('cancer_type'):
                print("\n" + "=" * 60)
                print("Onboarding voltooid!")
                print("=" * 60)
                
                # Fill in missing context with defaults
                if 'wellbeing' not in user_context:
                    user_context['wellbeing'] = 'niet gespecificeerd'
                if 'age' not in user_context:
                    user_context['age'] = 'niet gespecificeerd'
                if 'gender' not in user_context:
                    user_context['gender'] = 'niet gespecificeerd'
                if 'answer_style' not in user_context:
                    user_context['answer_style'] = 'eenvoudig en begrijpelijk'
                
                return user_context, last_user_input
            
            # Only show response if onboarding not complete
            if result.get('response'):
                print(f"\nAssistent: {result['response']}\n")
                
        except Exception as e:
            print(f"Fout tijdens onboarding: {str(e)}")
            # Fallback: extract cancer type directly
            user_context['cancer_type'] = user_input
            return user_context, user_input

def query_with_context(user_prompt: str, all_sections: list, cancer_type: str, user_context: dict = None, conversation_history: list = None) -> dict:
    """Query the model with specific cancer context"""
    # Find relevant sections
    relevant_sections = find_relevant_sections(user_prompt, all_sections, max_sections=5)
    context = "\n\n---\n\n".join(relevant_sections)
    
    # Build context-aware system message
    context_info = ""
    if user_context:
        context_info = "\n\nUSER CONTEXT:\n"
        if user_context.get('wellbeing'):
            context_info += f"- User wellbeing: {user_context['wellbeing']}\n"
        if user_context.get('age'):
            context_info += f"- Age: {user_context['age']}\n"
        if user_context.get('gender'):
            context_info += f"- Gender: {user_context['gender']}\n"
        if user_context.get('relation'):
            context_info += f"- Relation to cancer: {user_context['relation']}\n"
        if user_context.get('answer_style'):
            context_info += f"- Preferred answer style: {user_context['answer_style']}\n"
    
    # Build conversation history
    history_text = ""
    if conversation_history:
        history_text = "\n\nCONVERSATION HISTORY:\n"
        for i, (q, a) in enumerate(conversation_history[-3:], 1):  # Last 3 exchanges
            history_text += f"Q{i}: {q}\nA{i}: {a}\n\n"
    
    full_prompt = f"""You are a patient-focused medical information assistant for cancer-related topics.

Your role is to guide users using ONLY the provided information. You do not use outside knowledge.

-----------------------
CORE RULES
-----------------------

- Use only the provided information
- Do not assume, infer, or fill gaps
- If information is missing or unclear, say so explicitly
- Reflect uncertainty exactly as it appears in the information

Examples:
- "De informatie suggereert…"
- "Dit wordt niet duidelijk beschreven…"
- "Ik kan dit niet vinden in de beschikbare informatie."

-----------------------
GUIDED INTERACTION
-----------------------

Do not always answer immediately.

If a question is unclear, too broad, or lacks context:
- Ask 1–2 short clarifying questions before answering

-----------------------
INTERACTION STYLE
-----------------------

- Respect the user's wording and perspective
- Do not assume feelings, motives, or priorities
- Do not present interpretations as facts
- Keep responses concise and focused on one step at a time
- Invite correction when helpful

-----------------------
TONE
-----------------------

- Clear, calm, simple, and neutral
- Patient-friendly
- Not overly technical
- Not overly confident

-----------------------
LIMITATIONS
-----------------------

If the answer is not in the provided information:
- Say: "Ik kan dit niet vinden in de beschikbare informatie."
- Ask for clarification or suggest related topics

-----------------------
OUTPUT FORMAT (MANDATORY)
-----------------------

You must return the response in valid JSON only.

Structure:

{{
  "response": "string",
  "next_topics": ["string", "string", "string"],
  "references": ["string", "string"]
}}

Rules:
- "response":
  - Contains both the ANSWER and EXPLANATION combined into one clear text in Dutch
  - Include source URLs from the Referenties sections when available
  - Adapt tone and detail level based on user context
- "next_topics":
  - 3–5 short follow-up questions in Dutch
- "references":
  - URLs from the Referenties sections in the provided content

Constraints:
- Do not include any text outside the JSON
- Do not include markdown formatting
- Do not rename fields
- Ensure valid JSON (no trailing commas, correct quotes)

-----------------------
FINAL RULE
-----------------------

Stay strictly within the provided information.
If it is not stated, do not add it.
If it is uncertain, reflect that uncertainty.
{context_info}
{history_text}
-----------------------
PROVIDED INFORMATION ABOUT {cancer_type}
-----------------------

{context}

-----------------------
USER QUESTION
-----------------------

{user_prompt}

-----------------------
YOUR RESPONSE (JSON ONLY)
-----------------------"""
    
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 4096,
            "temperature": 0.3
        })
    )
    result = json.loads(response['body'].read())
    raw_content = result['choices'][0]['message']['content']
    
    # Strip reasoning tags if present
    if '<reasoning>' in raw_content:
        raw_content = raw_content.split('</reasoning>')[-1].strip()
    
    return json.loads(raw_content)

if __name__ == "__main__":
    # Load mapping
    cancer_mapping = load_cancer_mapping()
    
    # Onboarding
    user_context, initial_question = onboarding()
    
    if user_context is None:
        # User skipped onboarding
        print("\n" + "=" * 60)
        print("Cancer Assistant - Kanker Informatie Assistent")
        print("=" * 60)
        print(f"\n{len(cancer_mapping)} kankertypes beschikbaar.\n")
        print("Over welk type kanker wilt u informatie?")
        print("(Bijvoorbeeld: borstkanker, longkanker, leukemie, etc.)\n")
        cancer_choice = input("Kankertype: ").strip()
        user_context = {'cancer_type': cancer_choice}
        initial_question = None
    
    cancer_choice = user_context.get('cancer_type', '')
    
    if not cancer_choice:
        print("Geen kankertype opgegeven. Programma wordt afgesloten.")
        exit()
    
    # Find matching cancer type
    matched_type = find_best_match(cancer_choice, cancer_mapping)
    
    if not matched_type:
        print(f"\nKankertype '{cancer_choice}' niet gevonden in de database.")
        print("\nBeschikbare types:")
        for ct in sorted(cancer_mapping.keys())[:10]:
            print(f"  - {ct.title()}")
        print("  ... en meer")
        exit()
    
    # Load markdown content
    md_file = cancer_mapping[matched_type]
    content = load_markdown_content(md_file)
    
    if not content:
        print(f"\nFout: Kan bestand {md_file} niet laden.")
        exit()
    
    # Split into sections
    sections = chunk_markdown_by_sections(content)
    
    print(f"\n✓ Geladen: {matched_type.title()}")
    print(f"✓ Bron: {md_file}")
    print(f"✓ Secties: {len(sections)}")
    print("\nType 'exit', 'quit', of 'bye' om te stoppen\n")
    print("=" * 60)
    
    # Conversation history
    conversation_history = []
    
    # Answer initial question if present
    if initial_question and any(word in initial_question.lower() for word in ['informatie', 'info', 'vraag', 'vertel', 'wat', 'hoe', 'waarom', 'wanneer']):
        try:
            result = query_with_context(initial_question, sections, matched_type.title(), user_context, conversation_history)
            
            response_text = result['response']
            print(f"\n{response_text}")
            
            # Store in conversation history
            conversation_history.append((initial_question, response_text))
            
            if result.get('next_topics'):
                print("\n--- Vervolg onderwerpen ---")
                for topic in result['next_topics']:
                    print(f"  • {topic}")
            
            if result.get('references'):
                print("\n--- Bronnen ---")
                for ref in result['references']:
                    print(f"  • {ref}")
        except Exception as e:
            print(f"\nFout bij beantwoorden initiële vraag: {str(e)}")
    
    # Chat loop
    while True:
        prompt = input("\nVraag: ").strip()
        if not prompt:
            continue
        if prompt.lower() in ['exit', 'quit', 'bye']:
            break
        
        try:
            result = query_with_context(prompt, sections, matched_type.title(), user_context, conversation_history)
            
            response_text = result['response']
            print(f"\n{response_text}")
            
            # Store in conversation history
            conversation_history.append((prompt, response_text))
            
            if result.get('next_topics'):
                print("\n--- Vervolg onderwerpen ---")
                for topic in result['next_topics']:
                    print(f"  • {topic}")
            
            if result.get('references'):
                print("\n--- Bronnen ---")
                for ref in result['references']:
                    print(f"  • {ref}")
        except json.JSONDecodeError as e:
            print(f"\nFout: Kon het antwoord niet verwerken. JSON parse error: {str(e)}")
        except Exception as e:
            print(f"\nFout: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\nTot ziens!")