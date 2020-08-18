CREATE TABLE issue (
        id INTEGER NOT NULL,
        creation_date DATE NOT NULL,
        tracker VARCHAR(32) NOT NULL,
        category VARCHAR(32) NOT NULL,
        state VARCHAR(16) NOT NULL,
        description VARCHAR(255),
        CONSTRAINT issue_pk PRIMARY KEY (id),
        CONSTRAINT issue_tracker_uk UNIQUE (tracker)
);

CREATE SEQUENCE issue_id_seq;


CREATE TABLE model_issue_list_item (
        model_id INTEGER NOT NULL,
        issue_id INTEGER NOT NULL,
        CONSTRAINT model_issue_list_item_pk PRIMARY KEY (model_id, issue_id),
        CONSTRAINT model_issue_list_item_model_fk FOREIGN KEY(model_id) REFERENCES model (id),
        CONSTRAINT model_issue_list_item_issue_fk FOREIGN KEY(issue_id) REFERENCES issue (id) ON DELETE CASCADE
);

CREATE TABLE os_issue_list_item (
        os_id INTEGER NOT NULL,
        issue_id INTEGER NOT NULL,
        CONSTRAINT os_issue_list_item_pk PRIMARY KEY (os_id, issue_id),
        CONSTRAINT os_issue_list_item_os_fk FOREIGN KEY(os_id) REFERENCES operating_system (id),
        CONSTRAINT os_issue_list_item_issue_fk FOREIGN KEY(issue_id) REFERENCES issue (id) ON DELETE CASCADE
);

QUIT;
