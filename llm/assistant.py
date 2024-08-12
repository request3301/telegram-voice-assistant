from openai import OpenAI
from environment import Settings

client = OpenAI(api_key=Settings().OPENAI_API_KEY)

assistant = client.beta.assistants.create(
        model="gpt-4o",
        instructions="You are personal assistant. User can send you a picture of his face. "
                     "In this case you should analyse it's mood and answer correspondingly. "
                     "You also have access to an essay about anxiety. If you use it's content "
                     "in your answer, then you should tell about it. The answer will be sent to user in audio form.",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "save_value",
                    "description": "Save the user's key value.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "The user's key value."
                            }
                        },
                        "required": ["value"]
                    }
                }
            },
            {
                "type": "file_search"
            }
        ]
    )

print(assistant.id)
