from openai import OpenAI

from environment import Settings

client = OpenAI(api_key=Settings().OPENAI_API_KEY)

assistant = client.beta.assistants.create(
        model="gpt-4o",
        instructions="You are personal assistant. User can send you a picture of his face."
                     "In this case you should analyse it's mood and answer correspondingly.",
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
            }
        ]
    )

print(assistant.id)
