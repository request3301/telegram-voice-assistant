from pydantic import BaseModel
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from database.validation import validate
from environment import Settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Value(Base):
    __tablename__ = 'user_values'

    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[int]
    value: Mapped[str]


class PrFaq(Base):
    __tablename__ = 'pr_faq'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    title: Mapped[str]
    url: Mapped[str]


class PrFaqData(BaseModel):
    id: int
    user_id: int
    title: str
    url: str


engine = create_async_engine(Settings().DATABASE_URL, echo=True)

session_factory = async_sessionmaker(engine)


async def save_value(user: int, value: str):
    valid = await validate(value)
    print("user: ", user, "value: ", value, "valid: ", valid)
    if valid:
        async with session_factory() as session:
            await session.execute(insert(Value).values(user=user, value=value))
            await session.commit()


async def save_pr_faq(user_id: int, title: str, url: str):
    async with session_factory() as session:
        pr_faq = PrFaq(user_id=user_id, title=title, url=url)
        session.add(pr_faq)
        await session.commit()


async def get_all_pr_faqs(user_id: int):
    async with session_factory() as session:
        query = select(PrFaq).filter_by(user_id=user_id)
        result = await session.execute(query)
        result_orm = result.scalars().all()
        result_data = [PrFaqData.model_validate(row, from_attributes=True) for row in result_orm]
        return result_data
