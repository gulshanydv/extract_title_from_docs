import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_agent_data(agent_id, api_key):
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting agent data: {e}")
        return None

def update_agent_prompt():
    agent_id = os.getenv("AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not agent_id or not api_key:
        print("Error: AGENT_ID and ELEVENLABS_API_KEY must be set in your .env file.")
        return

    # Get current agent data
    print("Getting current agent data...")
    current_data = get_agent_data(agent_id, api_key)
    print(current_data,'AAAAAAAAAAAAAAAAAaaa')
    print(current_data['conversation_config']['agent']['first_message'])

    if current_data is None:
        return

    # Try to access the current prompt safely
    try:
        current_prompt = current_data['conversation_config']['agent']['prompt']['prompt']
        print(f"\nCurrent Prompt:\n{current_prompt}\n")
    except KeyError:
        print("Could not extract current prompt from agent data.")
        current_prompt = ""

    print("Updating prompt...\n" + "-" * 60)

    user = "Gulshan"
    first_prompt = """
        Hello {user}, I'm your personal medical assistant for medical support. How can I help you today?
    """.format(user=user)

   
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    payload = {
        "conversation_config": {
            "agent": {
                "first_message": first_prompt,
            }
        }
    }


    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Prompt updated successfully!")

        # Confirm update
        print("\nFetching updated agent data to confirm...")
        updated_data = get_agent_data(agent_id, api_key)
        
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error updating prompt: {e}")
        return None

if __name__ == "__main__":
    update_agent_prompt()
