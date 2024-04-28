# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2020  Contributor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Known issues related to model or os of hosts """

from datetime import datetime

from sqlalchemy import (
                        Column,
                        DateTime,
                        ForeignKey,
                        Integer,
                        PrimaryKeyConstraint,
                        Sequence,
                        )

from sqlalchemy.orm import (
                            backref,
                            deferred,
                            relationship,
                           )
from aquilon.aqdb.column_types import (
                                       AqStr,
                                       Enum,
                                      )
from aquilon.aqdb.model import (
                                Base,
                                Model,
                                OperatingSystem,
                               )

_TN = 'issue'
_MILI = 'model_issue_list_item'
_OILI = 'os_issue_list_item'
_STATES = ('open', 'closed', 'discarded')


class Issue(Base):

    __tablename__ = _TN

    id = Column(Integer, Sequence('issue_id_seq'), primary_key=True)

    creation_date = deferred(Column(DateTime, default=datetime.now,
                                    nullable=False))
    tracker = Column(AqStr(32), nullable=False, unique=True)

    category = Column(AqStr(32), nullable=False)

    state = Column(Enum(16, _STATES), nullable=False)

    description = Column(AqStr(255))

    __table_args__ = ({'info': {'unique_fields': ['tracker']}})


class __ModelIssueListItem(Base):

    __tablename__ = _MILI

    model_id = Column(ForeignKey(Model.id), nullable=False)

    issue_id = Column(ForeignKey(Issue.id, ondelete="CASCADE"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint(model_id, issue_id),)


Issue.models = relationship(Model,
                        secondary=__ModelIssueListItem.__table__,
                        backref=backref("issues"),
                        passive_deletes=True)


class __OSIssueListItem(Base):

    __tablename__ = _OILI

    os_id = Column(ForeignKey(OperatingSystem.id), nullable=False)

    issue_id = Column(ForeignKey(Issue.id, ondelete="CASCADE"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint(os_id, issue_id),)


Issue.os = relationship(OperatingSystem,
                    secondary=__OSIssueListItem.__table__,
                    backref=backref("issues"),
                    passive_deletes=True)
