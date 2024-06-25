from openai import OpenAI

from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

assistant = client.beta.assistants.create(
        model="gpt-4o",
        # tools=[
        #     {
        #         "type": "function",
        #         "function": {
        #             "name": "save_value",
        #             "description": "Save the user's key value.",
        #             "parameters": {
        #                 "type": "object",
        #                 "properties": {
        #                     "value": {
        #                         "type": "string",
        #                         "description": "The user's key value."
        #                     }
        #                 },
        #                 "required": ["value"]
        #             }
        #         }
        #     }
        # ]
    )

print(assistant.id)
