from db_session import SqlAlchemyBase
from sqlalchemy import Column, Integer, ForeignKey


# TODO: Доделать
class RelationshipMemberRole(SqlAlchemyBase):
    __tablename__ = "relationships_member_role"

    member_id = Column(Integer, ForeignKey('members.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
