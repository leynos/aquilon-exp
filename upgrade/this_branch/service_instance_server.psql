ALTER TABLE service_instance_server DROP CONSTRAINT service_instance_server_uk;
ALTER TABLE service_instance_server ADD CONSTRAINT service_instance_server_uk UNIQUE (service_instance_id, host_id, cluster_id, address_assignment_id, service_address_id, alias_id, address_id);
