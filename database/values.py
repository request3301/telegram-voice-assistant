from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs, AsyncSession
from sqlalchemy import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from environment import Settings
from database.validation import validate


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Value(Base):
    __tablename__ = 'user_values'

    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[int] = mapped_column()
    value: Mapped[str] = mapped_column()


engine = create_async_engine(Settings().DATABASE_URL, echo=True)


async def save_value(user: int, value: str):
    valid = await validate(value)
    print("user: ", user, "value: ", value, "valid: ", valid)
    if valid:
        async with AsyncSession(engine) as session:
            await session.execute(insert(Value).values(user=user, value=value))
            await session.commit()
