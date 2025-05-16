from langchain_openai import AzureChatOpenAI

class OpenAIModel:
    _instance = None

    @classmethod
    def get_instance(cls):
        """Returns an instance of AzureChatOpenAI (Runnable)."""
        if cls._instance is None:
            print("Creating new AzureChatOpenAI instance")
            cls._instance = cls.load_model()
        return cls._instance

    @staticmethod
    def load_model():
        """Loads and returns an AzureChatOpenAI instance."""
        print("Loading model in SDLCOpenAI")

        api_key="aae538b7d7cb4bcaa387fa1ecf5343a0"
        endpoint="https://rs-qm-openai-comp.openai.azure.com/openai/deployments/gpt4/chat/completions?api-version=2024-08-01-preview"
        version="2024-08-01-preview"
        deployment_name="gpt-4o"


        return AzureChatOpenAI(
            azure_endpoint=endpoint,
            openai_api_version=version,
            openai_api_key=api_key,
            deployment_name=deployment_name
        )
