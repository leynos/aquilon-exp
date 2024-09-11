import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import scoped_session


class TestBrokerCommand(unittest.TestCase):

    def setUp(self):
        self.session = MagicMock(spec=scoped_session)
        self.requestid = 'test_request_id'
        self.raising_exception = None
        self.rollback_failed = False
        self.start_rec = True
        self.requires_audit = True
        self._audit_result = None

    @patch('aquilon.worker.broker.end_xtn')
    @patch('aquilon.worker.broker.get_code_for_error_class')
    def test_end_xtn_called(self, mock_get_code_for_error_class, mock_end_xtn):
        mock_get_code_for_error_class.return_value = 200

        # Simulate the finally block
        if self.session:
            try:
                if self.requires_audit:
                    if not self.rollback_failed and self.start_rec:
                        mock_end_xtn(self.session, self.requestid,
                                     mock_get_code_for_error_class(self.raising_exception.__class__),
                                     self._audit_result)
            finally:
                self.session.remove()

        mock_end_xtn.assert_called_once_with(self.session, self.requestid, 200, self._audit_result)

    @patch('aquilon.worker.broker.end_xtn')
    def test_end_xtn_not_called_due_to_rollback_failed(self, mock_end_xtn):
        self.rollback_failed = True

        # Simulate the finally block
        if self.session:
            try:
                if self.requires_audit:
                    if not self.rollback_failed and self.start_rec:
                        mock_end_xtn(self.session, self.requestid,
                                     200, self._audit_result)
            finally:
                self.session.remove()

        mock_end_xtn.assert_not_called()

    @patch('aquilon.worker.broker.end_xtn')
    def test_end_xtn_not_called_due_to_start_rec_false(self, mock_end_xtn):
        self.start_rec = False

        # Simulate the finally block
        if self.session:
            try:
                if self.requires_audit:
                    if not self.rollback_failed and self.start_rec:
                        mock_end_xtn(self.session, self.requestid,
                                     200, self._audit_result)
            finally:
                self.session.remove()

        mock_end_xtn.assert_not_called()


if __name__ == '__main__':
    unittest.main()


