from llm.client import client
from environment import Settings


async def setup_filework():
    # Create a vector store called "Financial Statements"
    vector_store = await client.beta.vector_stores.create(name="Anxiety Essay")

    # Ready the files for upload to OpenAI
    file_paths = ["llm/files/Anxiety Essay.docx"]
    file_streams = [open(path, "rb") for path in file_paths]

    # Use the upload and poll SDK helper to upload the files, add them to the vector store,
    # and poll the status of the file batch for completion.
    await client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    await client.beta.assistants.update(
        assistant_id=Settings().ASSISTANT_ID,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )
