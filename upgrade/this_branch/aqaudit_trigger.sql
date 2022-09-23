CREATE OR REPLACE trigger xtn_id_delete
BEFORE DELETE ON xtn
FOR EACH ROW
BEGIN
	DELETE FROM xtn_detail WHERE xtn_id = :old.id;
	DELETE FROM xtn_end WHERE xtn_id = :old.id;
END;
/
