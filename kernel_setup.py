import os
import asyncio
from dotenv import load_dotenv
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

# Load environment variables
load_dotenv()

async def main():
    try:
        # Initialize chat service
        chat_service = AzureChatCompletion(
            deployment_name="legal-assistant",
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY")
        )
        print("✅ Chat service initialized")

        # Initialize chat agent
        agent = ChatCompletionAgent(
            service=chat_service,
            name="Legal-AI-Assistant",
            instructions="""You are an expert AI Legal Assistant specializing in artificial intelligence regulations worldwide. Your role is to:

1. Provide accurate, up-to-date information on AI laws, regulations, and compliance requirements across different jurisdictions
2. Explain complex legal concepts related to AI in clear, understandable terms
3. Help identify relevant regulatory requirements for AI applications and systems
4. Offer guidance on compliance strategies for AI development and deployment
5. Compare and contrast AI regulations across different regions
6. Identify potential legal risks and mitigation strategies
7. Stay updated on emerging AI legislation and regulatory trends
8. Provide context for historical development of AI laws and policies"""
        )
        print("✅ Chat agent initialized")
        return agent

    except Exception as e:
        print(f"❌ Error initializing kernel: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(main())