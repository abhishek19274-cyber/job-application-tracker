from typing import Optional
from datetime import date
from sqlalchemy import ForeignKey
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
from flask_login import UserMixin
db = SQLAlchemy()
from datetime import date, timedelta
# user table formation using SQLAlchemy
class User(UserMixin,db.Model):
    id : Mapped[int] = mapped_column(primary_key=True)
    email : Mapped[str] = mapped_column(unique=True)
    password_hash : Mapped[str]

#jobapplication table formation using SQLAlchemy where the two table are connected with user_id as a ForeignKey
class JobApplication(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    company : Mapped[str]
    role : Mapped[str]
    date_applied : Mapped[date] = mapped_column(default=date.today)
    status : Mapped[str] = mapped_column(default='Applied')
    deadline = db.Column(db.Date, nullable=True)
    file_name = db.Column(db.String, nullable=True)
    job_link : Mapped[Optional[str]]
    notes : Mapped[Optional[str]]
    user_id : Mapped[int] = mapped_column(ForeignKey('user.id'))

    @property
    def is_stale(self):
        return (date.today() - self.date_applied) > timedelta(days=14)

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "date_applied": self.date_applied.isoformat(),
            "status": self.status,
            "job_link": self.job_link,
            "notes": self.notes,
        }

