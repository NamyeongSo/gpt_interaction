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

# Configuration settings
CONFIG = {
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "max_tokens": int(os.getenv("MAX_TOKENS", "1000")),
    "temperature": float(os.getenv("TEMPERATURE", "0")),
    "top_p": float(os.getenv("TOP_P", "0")),
    "data_dir": os.getenv("DATA_DIR", "TACT_interraction_datas/multiwoz"),
                    "main_data_file": os.getenv("MAIN_DATA_FILE", "TACT_MultiWOZ_yjyoon_guide.json.json")
}

# Load sample data if needed (fallback when file loading fails)
def load_sample_data():
    sample_file = os.getenv("SAMPLE_DATA_FILE", "sample_data.json")
    sample_path = Path(sample_file)
    
    if sample_path.exists():
        try:
            with open(sample_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading sample data file: {str(e)}")
    
    # Return empty dictionary if no sample data available
    return {}

# Sample data as fallback
SAMPLE_DATA = load_sample_data()

# Load JSON file and extract available dialogue IDs
def load_json_data_and_extract_ids():
    dialogue_ids = []
    
    try:
        # First try to load from the JSON file
        nyso_file_path = Path(os.path.join(CONFIG["data_dir"], CONFIG["main_data_file"]))
        
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
    
    # If no IDs were loaded, use sample data
    if not dialogue_ids and SAMPLE_DATA:
        print("Using sample data")
        for dialogue_id in SAMPLE_DATA.keys():
            # Clean dialogue ID
            clean_id = dialogue_id.replace('.json', '')
            dialogue_ids.append({
                'id': clean_id,
                'file_path': 'sample_data',
                'file_name': 'Sample Data'
            })
    
    print(f"Total dialogue IDs available: {len(dialogue_ids)}")
    return dialogue_ids

# Get data for a specific dialogue ID
def get_dialogue_data(dialogue_id, file_path):
    # Try to get data from the sample data first for quick testing
    if SAMPLE_DATA and (dialogue_id in SAMPLE_DATA or dialogue_id + '.json' in SAMPLE_DATA):
        key = dialogue_id if dialogue_id in SAMPLE_DATA else dialogue_id + '.json'
        print(f"Using sample data for {key}")
        return SAMPLE_DATA[key], True
    
    # If not in sample data, try to load from file
    if file_path != 'sample_data' and Path(file_path).exists():
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
    
    # Fallback to first available dialogue in sample data if dialogue ID is not found
    if SAMPLE_DATA and len(SAMPLE_DATA) > 0:
        first_key = next(iter(SAMPLE_DATA))
        print(f"Using default sample data for {first_key}")
        return SAMPLE_DATA[first_key], False
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
    max_turns = int(os.getenv("MAX_SAMPLE_TURNS", "3"))
    for i in range(0, min(max_turns * 2, len(lines)), 2):
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
            model=CONFIG["openai_model"],
            messages=messages,
            temperature=CONFIG["temperature"],
            top_p=CONFIG["top_p"],
            max_tokens=CONFIG["max_tokens"]
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
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ["true", "1", "yes"]
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=debug_mode
    )