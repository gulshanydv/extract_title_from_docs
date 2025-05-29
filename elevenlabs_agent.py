import os
import signal
import sys
import requests
import json
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsAgentAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
    
    def get_agent_data(self, agent_id):
        """Get agent configuration data"""
        url = f"{self.base_url}/convai/agents/{agent_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting agent data: {e}")
            return None
    
    def update_agent_data(self, agent_id, agent_config):
        """Update agent configuration using PATCH endpoint"""
        url = f"{self.base_url}/convai/agents/{agent_id}"
        try:
            response = requests.patch(url, headers=self.headers, json=agent_config)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating agent data: {e}")
            return None
    
    def update_agent_prompt(self, agent_id, new_prompt):
        """Update only the agent's prompt"""
        agent_config = {
            "agent": {
                "prompt": {
                    "prompt": new_prompt
                }
            }
        }
        return self.update_agent_data(agent_id, agent_config)

   
def print_agent_info(agent_data):
    """Pretty print agent information"""
    if not agent_data:
        print("No agent data available")
        return
    
    print("\n" + "="*50)
    print("AGENT INFORMATION")
    print("="*50)
    
    # Common fields that might be in agent data
    fields_to_show = [
        'agent_id', 'name', 'description', 'voice_id', 
        'language', 'conversation_config', 'llm_config',
        'created_at', 'updated_at'
    ]
    
    for field in fields_to_show:
        if field in agent_data:
            value = agent_data[field]
            if isinstance(value, (dict, list)):
                print(f"{field.replace('_', ' ').title()}: {json.dumps(value, indent=2)}")
            else:
                print(f"{field.replace('_', ' ').title()}: {value}")
    
    print("="*50 + "\n")


def main():
    agent_id = os.getenv("AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    print(f"Agent ID: {agent_id}")
    print(f"API Key: {'*' * len(api_key) if api_key else 'Not provided'}")
    

    # Initialize API client for direct API calls
    api_client = ElevenLabsAgentAPI(api_key) if api_key else None
    
    # Get and display agent data
    if api_client:
        print("Fetching agent data...")
        agent_data = api_client.get_agent_data(agent_id)
        print_agent_info(agent_data)
        

    print(f"\nInitializing conversation with agent: {agent_id}")
    if api_key:
        print("Using authenticated mode (private agent)")
    else:
        print("Using public mode (no authentication)")
    
    try:
        elevenlabs = ElevenLabs(api_key=api_key)
        
        # Store conversation reference for later use
        conversation_obj = None

        conversation = Conversation(
            elevenlabs,
            agent_id,
            requires_auth=bool(api_key),
            audio_interface=DefaultAudioInterface(),
            callback_agent_response=lambda response: print(f"Agent: {response}"),
            callback_agent_response_correction=lambda original, corrected: print(f"Agent: {original} -> {corrected}"),
            callback_user_transcript=lambda transcript: print(f"User: {transcript}"),
            # Uncomment if you want to see latency measurements
            # callback_latency_measurement=lambda latency: print(f"Latency: {latency}ms"),
        )
        
        conversation_obj = conversation
        
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal. Ending conversation...")
            if conversation_obj:
                conversation_obj.end_session()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("Starting conversation session...")
        print("Speak into your microphone to interact with the AI agent.")
        print("Press Ctrl+C to end the conversation.")
        print("-" * 50)
        
        conversation.start_session()
        
        conversation_id = conversation.wait_for_session_end()
        
        print("-" * 50)
        print(f"Conversation ended. Conversation ID: {conversation_id}")
        
        # Try to fetch conversation history
        if api_client and conversation_id:
            print("Fetching conversation history...")
            history = api_client.get_conversation_history(conversation_id)
            if history:
                print("Conversation history retrieved successfully")
                # You can process and display the history here
                print(f"History keys: {list(history.keys())}")
        
        print("You can use this ID to review the conversation history.")
        
    except KeyboardInterrupt:
        print("\nConversation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

# Example function to update agent configuration
def update_agent_example():
    """Example of how to update agent configuration"""
    agent_id = os.getenv("AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not agent_id or not api_key:
        print("AGENT_ID and ELEVENLABS_API_KEY are required for updating agent")
        return
    
    api_client = ElevenLabsAgentAPI(api_key)
    
    # Example agent configuration update
    updated_config = {
        "name": "Updated Agent Name",
        "description": "Updated description",
        # Add other fields you want to update
        # "voice_id": "new_voice_id",
        # "language": "en",
        # "conversation_config": {...},
        # "llm_config": {...}
    }
    
    result = api_client.update_agent_data(agent_id, updated_config)
    if result:
        print("Agent updated successfully!")
        print(json.dumps(result, indent=2))
    else:
        print("Failed to update agent")

if __name__ == "__main__":
    # Uncomment the next line if you want to test agent updating
    # update_agent_example()
    
    main()