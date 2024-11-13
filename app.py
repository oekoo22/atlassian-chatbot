from dotenv import load_dotenv
import os

load_dotenv()

# Atlassian Key
atlassian_key = os.getenv("ATLASSIAN_API")

print("API Key loaded:", atlassian_key is not None)