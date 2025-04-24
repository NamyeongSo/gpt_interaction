# GPT-4o-mini Chat Web Interface

A simple web application for interacting with OpenAI's GPT-4o-mini model, with support for system prompts and dialog history.

# 아래를 따라하세요~
- requirement install
- .env파일에 openai api key 입력
- \TACT_interraction_datas\multiwoz 폴더 하단에 자신 이름의 json 파일 위치하게 하기(현재는 nyso파일이 위치함)
- python app.py로 실행

## Features

- Send messages to GPT-4o-mini
- Set system prompts to guide AI behavior
- View and maintain dialog history
- Clear conversation history when needed
- User-friendly web interface

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```
4. Add your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   SECRET_KEY=your_random_secret_key_here
   ```

## Running the Application

Start the Flask server:

```
python app.py
```

Then open your browser and navigate to:
```
http://127.0.0.1:5000
```

## Usage

1. **System Prompt**: Enter instructions for the AI in the system prompt field. This sets the behavior and context for the AI but is not shown in the chat history.

2. **User Messages**: Type your message in the input field at the bottom and press "Send" or hit Enter.

3. **Clear History**: To start a new conversation, click the "Clear Chat History" button.

## Note

This application uses Flask sessions to store conversation history, which means the history is tied to your browser session. Closing the browser or clearing cookies will reset the conversation. 
