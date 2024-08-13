import json

from llm.client import client

tools = [
    {
        "type": "function",
        "function": {
            "name": "write_to_database",
            "description": "If the message is valid then function passes True as parameter and it is written to database."
                           "Otherwise, function passes False as parameter and the message is ignored.",
            "parameters": {
                "type": "object",
                "properties": {
                    "valid": {
                        "type": "boolean",
                        "description": """Message is valid if and only if it can represent a human's value. Don't be strict, values can differ alot.
                                          Examples of valid messages:
                                          "Honesty",
                                          "Good taste in music",
                                          "Egocentrism",
                                          "J. K. Rowling's books",
                                          "Values history and enjoys visiting historical places to understand and honor the past".
                                          Examples of invalid messages:
                                          "My age is 30",
                                          "Nike is better than Adidas".
                                          """,
                    },
                },
                "required": ["valid"],
            },
        }
    },
]

tool_choice = {"type": "function", "function": {"name": "write_to_database"}}


async def validate(value: str) -> bool:
    messages = [{"role": "user", "content": value}]
    chat_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )
    response_message = chat_response.choices[0].message
    tool_calls = response_message.tool_calls
    valid = json.loads(tool_calls[0].function.arguments)['valid']
    return valid
