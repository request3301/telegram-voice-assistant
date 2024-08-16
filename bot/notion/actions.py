from notion.client import notion, domain, database_id


def split_text(text):
    return text.split('\n')


async def create_page(title: str, text: str) -> str:
    response = await notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "title": [
                {
                    "type": "text",
                    "text": {"content": title}
                }
            ]
            # TODO add page content
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": chunk}
                        }
                    ]
                }
            } for chunk in split_text(text)
        ],
    )
    url_title = title.replace(" ", "-")
    page_id = response['id'].replace("-", "")
    page_url = f"https://{domain}.notion.site/{url_title}-{page_id}"
    return page_url
