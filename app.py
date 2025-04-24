from flask import Flask, render_template, request, jsonify, session
import openai
import os
import json
import re
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Get API key and print debug info (without exposing the full key)
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"API key found: {api_key[:8]}...{api_key[-4:]}")
else:
    print("WARNING: No OpenAI API key found in environment variables!")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")

# Initialize OpenAI client
client = openai.OpenAI(api_key=api_key)

# Hard-coded sample data structure from TACT_MultiWOZ_nyso_guide.json
NYSO_DATA = {
    "PMUL3156.json": {
        "guideline": """0 [USER] [find_restaurant] I'm trying to find information about a particular restaurant called Ian Hong house.
1 [SYSTEM] 
2 [USER] [find_restaurant] 
3 [SYSTEM] 
4 [USER] [find_restaurant] 
5 [SYSTEM] 
6 [USER] [chitchat] Oh, I love Chinese food! Do you know if they have any good vegetarian options?
7 [SYSTEM] 
8 [USER] [chitchat] 
9 [SYSTEM] [Transition to ToD] 
10 [USER] [book_hotel] 8 people. 5 nights, starting from Wednesday. Please give me the reference number, please.
11 [SYSTEM] 
12 [USER] [book_taxi] I would like to book a taxi from the Hong House to the hotel leaving by 10:15.
13 [SYSTEM] 
14 [USER] [NONE] Wonderful, thank you for everything.
15 [SYSTEM] 
16 [USER] [book_taxi] One more thing. Can you please give me the taxi contact number?
17 [SYSTEM] """,
        "generated_data": """0 [USER] [find_restaurant] I'm trying to find information about a particular restaurant called Ian Hong house.
1 [SYSTEM] Our records don't show that hotel. Sorry.
2 [USER] [find_restaurant] Are you sure you don't have anything on Ian Hong House? I need the address and postcode.
3 [SYSTEM] Yes, I am sure. There is no Ian Hong House restaurant in our system.
4 [USER] [find_restaurant] Can you please check again? Lan Hong House.
5 [SYSTEM] Sorry about that! I found the Lan Hong House at 12 Norfolk Street City Centre, CB1 2LF. It's a moderately-priced Chinese restaurant.
6 [USER] [chitchat] Oh, I love Chinese food! Do you know if they have any good vegetarian options?
7 [SYSTEM] That's great to hear! Many Chinese restaurants do offer a variety of vegetarian dishes, so you should find some tasty options at Lan Hong House.
8 [USER] [chitchat] Perfect! I always appreciate a good veggie dish. By the way, can I also get help booking a room at the Huntingdon Marriott Hotel, please?
9 [SYSTEM] [Transition to ToD] Sure! For what length of stay and how many people, please?
10 [USER] [book_hotel] 8 people. 5 nights, starting from Wednesday. Please give me the reference number, please.
11 [SYSTEM] Your booking was successful. The reference number is: USRCWCJ 0. Can I help you with anything else?
12 [USER] [book_taxi] I would like to book a taxi from the Hong House to the hotel leaving by 10:15.
13 [SYSTEM] No problem. I booked a red Audi that will pick you up by 10:15.
14 [USER] [NONE] Wonderful, thank you for everything.
15 [SYSTEM] Have a great trip! Thank you for contacting us for all your booking needs. Enjoy your trip!
16 [USER] [book_taxi] One more thing. Can you please give me the taxi contact number?
17 [SYSTEM] Sure! The contact number is 07686386258. The car will be a red Audi."""
    },
    "PMUL2296.json": {
        "guideline": """0 [USER] [find_restaurant] Hello, I can't wait to try some local restaurants when I travel there next week. I could use some help with places to go in town though.
1 [SYSTEM] 
2 [USER] [find_attraction] Actually, is there a place in town that offers nice architecture to see?
3 [SYSTEM] 
4 [USER] [find_restaurant] I want a place that has Latin food.
5 [SYSTEM] 
6 [USER] [find_restaurant] 
7 [SYSTEM] 
8 [USER] [book_restaurant] Yes, I would like to reserve a table for a party of 8 at 16:00 on Friday. I've also got another question when you're done with that. Thank you.
9 [SYSTEM] 
10 [USER] [book_restaurant] 
11 [SYSTEM] 
12 [USER] [book_taxi] I would like a cab to and from both places please make sure it is on time so I don't miss my reservation, contact # & car type.
13 [SYSTEM] 
14 [USER] [find_attraction] I will be leaving from the restaurant.
15 [SYSTEM] 
16 [USER] [find_attraction] 
17 [SYSTEM] 
18 [USER] [find_attraction] 
19 [SYSTEM] 
20 [USER] [chitchat] That sounds fine! By the way, I really enjoy visiting places with unique designs. Do you know if there are any other interesting architectural spots nearby?
21 [SYSTEM] 
22 [USER] [book_taxi] Can you get me a taxi from there to the restaurant? I'll need to arrive by 16:00 for my reservation.
23 [SYSTEM] """,
        "generated_data": """0 [USER] [find_restaurant] Hello, I can't wait to try some local restaurants when I travel there next week. I could use some help with places to go in town though.
1 [SYSTEM] I'm certain we can help with that. Do you have a price range, part of town or what kind of food you'll want to eat?
2 [USER] [find_attraction] Actually, is there a place in town that offers nice architecture to see?
3 [SYSTEM] There is a moderate priced Asian restaurant in the centre called Yippee Noodle Bar that's around beautiful places. Would you like to try that?
4 [USER] [find_restaurant] I want a place that has Latin food.
5 [SYSTEM] I'm very sorry I am finding no results for restaurants serving Latin food. Is there another type of cuisine you'd be interested in?
6 [USER] [find_restaurant] How about some Vietnamese food in the west then?
7 [SYSTEM] I have the Thanh Binh restaurant located at 17 Magdalene Street City Centre. Would you like reservations?
8 [USER] [book_restaurant] Yes, I would like to reserve a table for a party of 8 at 16:00 on Friday. I've also got another question when you're done with that. Thank you.
9 [SYSTEM] Booking was successful. The table will be reserved for 15 minutes. Reference number is: Q4NHOJRD. What was the other question?
10 [USER] [book_restaurant] You must be a mind reader, my question was the reference number! Thank you.
11 [SYSTEM] You're very welcome! Is there anything else I can help you with?
12 [USER] [book_taxi] I would like a cab to and from both places please make sure it is on time so I don't miss my reservation, contact # & car type.
13 [SYSTEM] What place will you be leaving from?
14 [USER] [find_attraction] I will be leaving from the restaurant.
15 [SYSTEM] Well, you didn't suggest any attractions, you see. What would you suggest, then I can schedule my cab after that?
16 [USER] [find_attraction] My apologies! My wife loves architecture and insisted I find a place, glad I didn't forget. Any area's fine, but what about the same as the restaurant?
17 [SYSTEM] Is there a price range would you like?
18 [USER] [find_attraction] I'd like a place to go to in the category of architecture, preferably free.
19 [SYSTEM] All Saints Church is free and located on Jesus Lane.
20 [USER] [chitchat] That sounds fine! By the way, I really enjoy visiting places with unique designs. Do you know if there are any other interesting architectural spots nearby?
21 [SYSTEM] Oh, there are definitely some unique spots! The University of Cambridge has some stunning buildings, like the King's College Chapel, which is a must-see.
22 [USER] [book_taxi] Can you get me a taxi from there to the restaurant? I'll need to arrive by 16:00 for my reservation.
23 [SYSTEM] Your taxi has been booked. You will be picked up in a white Volvo. The contact number is 07266032951. May I be of further assistance today?"""
    }
}

# Load JSON file and extract available dialogue IDs
def load_json_data_and_extract_ids():
    dialogue_ids = []
    
    try:
        # First try to load from the JSON file
        nyso_file_path = Path('TACT_interraction_datas/multiwoz/TACT_MultiWOZ_nyso_guide.json')
        
        if nyso_file_path.exists():
            try:
                with open(nyso_file_path, 'r', encoding='utf-8-sig') as f:
                    try:
                        data = json.load(f)
                        for dialogue_id in data.keys():
                            # Clean dialogue ID (remove .json extension if present)
                            clean_id = dialogue_id.replace('.json', '')
                            dialogue_ids.append({
                                'id': clean_id,
                                'file_path': str(nyso_file_path),
                                'file_name': nyso_file_path.name
                            })
                        print(f"Successfully loaded {len(dialogue_ids)} dialogue IDs from {nyso_file_path}")
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error in {nyso_file_path}: {str(e)}")
            except Exception as e:
                print(f"Error loading file {nyso_file_path}: {str(e)}")
    except Exception as e:
        print(f"Error during file loading: {str(e)}")
    
    # If no IDs were loaded, use hardcoded sample data
    if not dialogue_ids:
        print("Using hardcoded sample data")
        for dialogue_id in NYSO_DATA.keys():
            # Clean dialogue ID
            clean_id = dialogue_id.replace('.json', '')
            dialogue_ids.append({
                'id': clean_id,
                'file_path': 'hardcoded',
                'file_name': 'NYSO Sample Data'
            })
    
    print(f"Total dialogue IDs available: {len(dialogue_ids)}")
    return dialogue_ids

# Get data for a specific dialogue ID
def get_dialogue_data(dialogue_id, file_path):
    # Try to get data from the hardcoded sample first for quick testing
    if dialogue_id in NYSO_DATA or dialogue_id + '.json' in NYSO_DATA:
        key = dialogue_id if dialogue_id in NYSO_DATA else dialogue_id + '.json'
        print(f"Using hardcoded data for {key}")
        return NYSO_DATA[key], True
    
    # If not in hardcoded data, try to load from file
    if file_path != 'hardcoded' and Path(file_path).exists():
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                
                # Check for dialogue ID in the data
                if dialogue_id in data:
                    dialogue_data = data[dialogue_id]
                    if "guideline" in dialogue_data and "generated_data" in dialogue_data:
                        return dialogue_data, True
                elif dialogue_id + '.json' in data:
                    dialogue_data = data[dialogue_id + '.json']
                    if "guideline" in dialogue_data and "generated_data" in dialogue_data:
                        return dialogue_data, True
                else:
                    print(f"Dialogue ID {dialogue_id} not found in file")
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
    
    # Fallback to default data if dialogue ID is not found
    if 'PMUL3156' in NYSO_DATA or 'PMUL3156.json' in NYSO_DATA:
        key = 'PMUL3156.json'  # Default to this dialogue
        print(f"Using default hardcoded data for {key}")
        return NYSO_DATA[key], False
    else:
        # Ultimate fallback
        return {
            "guideline": "",
            "generated_data": ""
        }, False

# Extract and format example dialogs
def extract_sample_dialogs(data_string):
    lines = data_string.strip().split('\n')
    sample_dialogs = []
    
    # Process first three turns (pairs of lines)
    for i in range(0, min(6, len(lines)), 2):
        if i+1 < len(lines):
            user_line = lines[i]
            system_line = lines[i+1]
            
            # Extract user message (remove turn number and tags)
            user_match = re.search(r'^\d+ \[USER\] \[[^\]]+\] (.*)', user_line)
            user_content = user_match.group(1) if user_match else user_line
            
            # Extract system response (remove turn number and tags)
            system_match = re.search(r'^\d+ \[SYSTEM\]( \[[^\]]+\])? (.*)', system_line)
            system_content = system_match.group(2) if system_match else system_line
            
            sample_dialogs.append({
                'dialogue_id': f"Turn {(i//2) + 1}",
                'user': user_content,
                'assistant': system_content
            })
    
    return sample_dialogs

@app.route('/')
def index():
    # Initialize dialog history if it doesn't exist
    if 'messages' not in session:
        session['messages'] = []
    
    # Get list of dialogue IDs
    dialogue_ids = load_json_data_and_extract_ids()
    
    # Get selected dialogue ID
    selected_id = request.args.get('dialogue_id')
    selected_dialogue = None
    
    # Find the selected dialogue or use the first one
    if selected_id:
        for dialogue in dialogue_ids:
            if dialogue['id'] == selected_id:
                selected_dialogue = dialogue
                break
    
    if not selected_dialogue and dialogue_ids:
        selected_dialogue = dialogue_ids[0]
        selected_id = selected_dialogue['id']
    
    # Get dialogue data
    if selected_dialogue:
        dialogue_data, success = get_dialogue_data(selected_dialogue['id'], selected_dialogue['file_path'])
        file_source = selected_dialogue['file_name']
    else:
        dialogue_data = {"guideline": "", "generated_data": ""}
        success = False
        file_source = "No Data Available"
    
    # Extract guideline and generated data
    guideline = dialogue_data.get("guideline", "")
    generated_data = dialogue_data.get("generated_data", "")
    
    # Create sample dialogs
    sample_dialogs = extract_sample_dialogs(generated_data)
    
    data_source = f"{file_source} - {selected_id}" if success else "No valid data"
    
    return render_template('index.html', 
                          messages=session['messages'],
                          guidelines=guideline,
                          sample_dialogs=sample_dialogs,
                          dialogue_ids=dialogue_ids,
                          selected_id=selected_id,
                          data_source=data_source)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    system_prompt = data.get('system_prompt', '')
    user_prompt = data.get('user_prompt', '')
    
    # Initialize messages if they don't exist
    if 'messages' not in session:
        session['messages'] = []
    
    # Create messages array for OpenAI API
    messages = []
    
    # Add system message at the beginning
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Add accumulated dialog history
    for msg in session['messages']:
        messages.append({"role": msg['role'], "content": msg['content']})
    
    # Add current user message
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
        # Save to session history
        session['messages'].append({"role": "user", "content": user_prompt})
        # Force session to persist changes
        session.modified = True
    
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            top_p=0,
            max_tokens=1000
        )
        
        # Extract assistant response
        assistant_message = response.choices[0].message.content
        
        # Save assistant response to session history
        session['messages'].append({"role": "assistant", "content": assistant_message})
        session.modified = True
        
        return jsonify({
            "response": assistant_message,
            "messages": session['messages']
        })
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    session['messages'] = []
    session.modified = True
    return jsonify({"status": "success", "messages": []})

if __name__ == '__main__':
    app.run(debug=True) 