ALTER TABLE service_instance_server ADD address_id INTEGER;
ALTER TABLE service_instance_server ADD CONSTRAINT sis_address_fk FOREIGN KEY (address_id) REFERENCES a_record(dns_record_id);
