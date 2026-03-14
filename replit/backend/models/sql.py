from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, DateTime, func, UUID, Double

class Base(DeclarativeBase): pass

class MessageLog(Base):
    __tablename__ = "LlmApp_messagelog"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    home_country: Mapped[str] = mapped_column(Text, nullable=False)
    host_country: Mapped[str] = mapped_column(Text, nullable=False)
    date_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now(), nullable=False)

class Summary(Base):
    __tablename__ = "LlmApp_summary"
    user_id: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    last_session_id: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now(), nullable=False)

class Session(Base):
    __tablename__ = "LlmApp_session"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=func.gen_random_uuid())
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),  
                                                server_default=func.now(), nullable=False)
    last_activity_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                server_default=func.now(), nullable=False)

class MessageLogLink(Base):
    __tablename__ = "LlmApp_messagelog_link"
    message_id: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)

class PartySupport(Base):
    __tablename__ = "LlmApp_partysupport"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    group_variable: Mapped[str] = mapped_column(Text, nullable=False)
    group_label: Mapped[str] = mapped_column(Text, nullable=False)
    n: Mapped[int] = mapped_column(BigInteger, nullable=True)
    n_flag: Mapped[str] = mapped_column(Text, nullable=True)
    pct_lib: Mapped[float] = mapped_column(Double, nullable=True)
    pct_con: Mapped[float] = mapped_column(Double, nullable=True)
    pct_ndp: Mapped[float] = mapped_column(Double, nullable=True)
    pct_bq: Mapped[float] = mapped_column(Double, nullable=True)
    pct_grn: Mapped[float] = mapped_column(Double, nullable=True)
    pct_other: Mapped[float] = mapped_column(Double, nullable=True)
    pct_none: Mapped[float] = mapped_column(Double, nullable=True)
    none_label: Mapped[str] = mapped_column(Text, nullable=True)
    year: Mapped[int] = mapped_column(BigInteger, nullable=True)
    dataset: Mapped[str] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                   server_default=func.now(), nullable=False)