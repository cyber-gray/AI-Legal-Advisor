import os
import asyncio
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings

# Load environment variables
load_dotenv()

async def main():
    # Initialize chat service
    chat_service = AzureChatCompletion(
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY")
    )
    
    print("Chat service initialized successfully!")
    
    # Create chat history with a message
    chat_history = ChatHistory()
    chat_history.add_user_message("Hello! Are you working?")
    
    # Create settings for the chat completion
    settings = PromptExecutionSettings()
    
    # Get completion from the service
    response = await chat_service.get_chat_message_contents(chat_history=chat_history, settings=settings)
    print(f"Response: {response[0].content}")

if __name__ == "__main__":
    asyncio.run(main())