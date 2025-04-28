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
    "main_data_file": os.getenv("MAIN_DATA_FILE", "TACT_MultiWOZ_yjyoon_guide.json"),
    "alternative_data_files": [
        "TACT_MultiWOZ_nyso_guide.json",
        "TACT_MultiWOZ_yjyoon_guide.json.json"
    ]
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
    
    # Helper function to process a single file
    def process_file(file_path):
        file_dialogue_ids = []
        try:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8-sig') as f:
                        try:
                            data = json.load(f)
                            for dialogue_id in data.keys():
                                # Keep the original dialogue ID with .json extension
                                file_dialogue_ids.append({
                                    'id': dialogue_id,
                                    'file_path': str(file_path),
                                    'file_name': file_path.name
                                })
                            print(f"Successfully loaded {len(file_dialogue_ids)} dialogue IDs from {file_path}")
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error in {file_path}: {str(e)}")
                except Exception as e:
                    print(f"Error loading file {file_path}: {str(e)}")
        except Exception as e:
            print(f"Error during file loading: {str(e)}")
        return file_dialogue_ids
    
    # First try the main file
    main_file_path = Path(os.path.join(CONFIG["data_dir"], CONFIG["main_data_file"]))
    dialogue_ids.extend(process_file(main_file_path))
    
    # If we didn't find any dialogue IDs, try the alternative files
    if not dialogue_ids:
        for alt_file in CONFIG["alternative_data_files"]:
            alt_file_path = Path(os.path.join(CONFIG["data_dir"], alt_file))
            file_ids = process_file(alt_file_path)
            dialogue_ids.extend(file_ids)
            if file_ids:  # If we found IDs, no need to check more files
                break
    
    # If no IDs were loaded, use sample data
    if not dialogue_ids and SAMPLE_DATA:
        print("Using sample data")
        for dialogue_id in SAMPLE_DATA.keys():
            # Keep original dialogue ID format for sample data
            dialogue_ids.append({
                'id': dialogue_id,
                'file_path': 'sample_data',
                'file_name': 'Sample Data'
            })
    
    print(f"Total dialogue IDs available: {len(dialogue_ids)}")
    return dialogue_ids

# Get data for a specific dialogue ID
def get_dialogue_data(dialogue_id, file_path):
    # Try to get data from the sample data first for quick testing
    if SAMPLE_DATA:
        # Try with the exact ID first
        if dialogue_id in SAMPLE_DATA:
            print(f"Using sample data for {dialogue_id}")
            return SAMPLE_DATA[dialogue_id], True
        
        # If the ID doesn't have .json extension, try adding it
        if not dialogue_id.endswith('.json') and dialogue_id + '.json' in SAMPLE_DATA:
            print(f"Using sample data for {dialogue_id}.json")
            return SAMPLE_DATA[dialogue_id + '.json'], True
    
    # Function to try loading data from a specific file
    def try_file(path, id):
        if path == 'sample_data' or not Path(path).exists():
            return None, False
        
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                
                # Try exact match
                if id in data:
                    dialogue_data = data[id]
                    if "guideline" in dialogue_data and "generated_data" in dialogue_data:
                        print(f"Found dialogue {id} in {path}")
                        return dialogue_data, True
                
                # Try with .json extension
                id_with_json = id if id.endswith('.json') else id + '.json'
                if id_with_json in data:
                    dialogue_data = data[id_with_json]
                    if "guideline" in dialogue_data and "generated_data" in dialogue_data:
                        print(f"Found dialogue {id_with_json} in {path}")
                        return dialogue_data, True
                
                # Try approximate matching
                possible_matches = [k for k in data.keys() if id.replace('.json', '') in k or k.replace('.json', '') in id]
                if possible_matches:
                    match_id = possible_matches[0]
                    dialogue_data = data[match_id]
                    if "guideline" in dialogue_data and "generated_data" in dialogue_data:
                        print(f"Found similar dialogue {match_id} in {path}")
                        return dialogue_data, True
        except Exception as e:
            print(f"Error reading file {path}: {str(e)}")
        
        return None, False
    
    # First try the specified file path
    result, success = try_file(file_path, dialogue_id)
    if success:
        return result, success
    
    # If not found and file_path is not from sample data, try alternative files
    if file_path != 'sample_data':
        data_dir = CONFIG["data_dir"]
        
        # First try main data file if it's different from the specified file
        main_file_path = os.path.join(data_dir, CONFIG["main_data_file"])
        if main_file_path != file_path:
            result, success = try_file(main_file_path, dialogue_id)
            if success:
                return result, success
        
        # Then try alternative files
        for alt_file in CONFIG["alternative_data_files"]:
            alt_file_path = os.path.join(data_dir, alt_file)
            if alt_file_path != file_path:  # Don't retry the same file
                result, success = try_file(alt_file_path, dialogue_id)
                if success:
                    return result, success
    
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
                'agent': system_content
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
        
        # Extract agent response
        agent_message = response.choices[0].message.content
        
        # Save agent response to session history
        session['messages'].append({"role": "agent", "content": agent_message})
        session.modified = True
        
        return jsonify({
            "response": agent_message,
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

@app.route('/api/save-history', methods=['POST'])
def save_history():
    if 'messages' not in session or not session['messages']:
        return jsonify({"status": "error", "message": "No dialogue history to save"}), 400
    
    selected_id = request.json.get('dialogue_id')
    if not selected_id:
        return jsonify({"status": "error", "message": "No dialogue ID provided"}), 400
    
    def try_save_to_file(file_path, dialogue_id):
        """Try to save dialogue history to the specified file path"""
        try:
            if not file_path.exists():
                print(f"Data file not found: {file_path}")
                return None, f"Data file not found: {file_path}"
            
            # Load the current data
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            
            # Debug: Print the available dialogue IDs
            print(f"File: {file_path}")
            print(f"Available dialogue IDs in file: {list(data.keys())[:5]} (showing first 5)")
            print(f"Looking for dialogue ID: {dialogue_id}")
            
            # Ensure dialogue ID has .json extension for lookup
            dialogue_id_with_json = dialogue_id if dialogue_id.endswith('.json') else dialogue_id + '.json'
            
            # Check if the dialogue ID exists (try both with and without .json)
            if dialogue_id_with_json in data:
                # Add the dialogue history to the dialogue data
                data[dialogue_id_with_json]["dialogue_history"] = session['messages']
                print(f"Saved history to {dialogue_id_with_json}")
                
                # Save the updated data back to the file
                with open(file_path, 'w', encoding='utf-8-sig') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return True, None
            elif dialogue_id in data:
                # If the ID without .json exists
                data[dialogue_id]["dialogue_history"] = session['messages']
                print(f"Saved history to {dialogue_id}")
                
                # Save the updated data back to the file
                with open(file_path, 'w', encoding='utf-8-sig') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return True, None
            else:
                # Try approximate matching
                possible_matches = [k for k in data.keys() if dialogue_id.replace('.json', '') in k or k.replace('.json', '') in dialogue_id]
                if possible_matches:
                    print(f"Possible matches found: {possible_matches}")
                    # Use the first match
                    match_id = possible_matches[0]
                    data[match_id]["dialogue_history"] = session['messages']
                    print(f"Saved history to closest match: {match_id}")
                    
                    # Save the updated data back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    return True, match_id
            
            return False, f"Dialogue ID {dialogue_id} not found in {file_path.name}"
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return None, str(e)
    
    # First try the main data file
    main_file_path = Path(os.path.join(CONFIG["data_dir"], CONFIG["main_data_file"]))
    result, message = try_save_to_file(main_file_path, selected_id)
    
    # If successful, return success
    if result == True:
        success_message = "Dialogue history saved successfully"
        if message:  # If we found an approximate match
            success_message = f"Dialogue history saved to closest match: {message}"
        return jsonify({"status": "success", "message": success_message})
    
    # If main file doesn't exist or doesn't contain the ID, try alternative files
    for alt_file in CONFIG["alternative_data_files"]:
        alt_file_path = Path(os.path.join(CONFIG["data_dir"], alt_file))
        print(f"Trying alternative file: {alt_file_path}")
        result, message = try_save_to_file(alt_file_path, selected_id)
        
        # If successful, return success
        if result == True:
            success_message = f"Dialogue history saved to {alt_file}"
            if message:  # If we found an approximate match
                success_message = f"Dialogue history saved to closest match: {message} in {alt_file}"
            return jsonify({"status": "success", "message": success_message})
    
    # If we get here, no file contained the dialogue ID
    return jsonify({"status": "error", "message": f"Dialogue ID {selected_id} not found in any data file"}), 404

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ["true", "1", "yes"]
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=debug_mode
    )