import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

class LegalAssistant:
    def __init__(self):
        load_dotenv()
        self.chat_history: List[Dict] = []
        self.chat_client = None
        self.system_prompt = """You are an expert AI Legal Assistant specializing in artificial intelligence regulations worldwide. 
        When answering questions:
        1. Provide accurate, up-to-date information on AI laws and regulations
        2. Cite specific legal documents or sources when available
        3. Explain complex legal concepts in clear terms
        4. Consider multiple jurisdictions when relevant
        5. Clearly state when information may require verification
        Remember to recommend consulting with legal professionals for specific legal advice."""

    async def initialize(self):
        """Initialize chat client"""
        try:
            self.chat_client = ChatCompletionsClient(
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_KEY")),
                api_version="2024-02-15-preview"
            )
            print("✅ Legal Assistant initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Initialization error: {str(e)}")
            return False

    async def get_response(self, user_input: str) -> Optional[str]:
        """Get response from the AI assistant"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            # Add chat history context for continuity
            for history in self.chat_history[-3:]:  # Include last 3 interactions for context
                messages.append({"role": "user", "content": history["user_input"]})
                messages.append({"role": "assistant", "content": history["assistant_response"]})
            
            # Get new response using the correct API
            response = await self.chat_client.get_chat_completions(
                model="legal-assistant",  # This is your deployment name
                messages=messages
            )
            
            response_content = response.choices[0].message.content
            
            # Store the interaction in chat history
            self.chat_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "assistant_response": response_content
            })
            
            return response_content
        except Exception as e:
            print(f"❌ Error getting response: {str(e)}")
            return None

    def save_chat_history(self, filename: str = "chat_history.txt"):
        """Save the chat history to a file"""
        try:
            with open(filename, "w") as f:
                for interaction in self.chat_history:
                    f.write(f"Time: {interaction['timestamp']}\n")
                    f.write(f"User: {interaction['user_input']}\n")
                    f.write(f"Assistant: {interaction['assistant_response']}\n")
                    f.write("-" * 80 + "\n")
            print(f"✅ Chat history saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving chat history: {str(e)}")

async def main():
    """Main function to run the legal assistant"""
    print("\nInitializing AI Legal Assistant...")
    print("This assistant uses Azure AI Inference for enhanced capabilities.\n")
    
    assistant = LegalAssistant()
    if not await assistant.initialize():
        return

    print("\nAI Legal Assistant is ready!")
    print("Type 'exit' to end the conversation, 'save' to save chat history\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'exit':
                print("\nGoodbye! Saving chat history...")
                assistant.save_chat_history()
                break
            elif user_input.lower() == 'save':
                assistant.save_chat_history()
                continue
            elif not user_input:
                continue

            response = await assistant.get_response(user_input)
            if response:
                print("\nAssistant:", response)
            else:
                print("\n❌ Failed to get response. Please try again.")

        except KeyboardInterrupt:
            print("\n\nReceived interrupt signal. Saving chat history before exit...")
            assistant.save_chat_history()
            break
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {str(e)}")
            print("The application will continue running. You can try again or type 'exit' to quit.")

if __name__ == "__main__":
    asyncio.run(main())