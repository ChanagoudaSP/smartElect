DROP DATABASE IF EXISTS evoting_db;
CREATE DATABASE evoting_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE evoting_db;

CREATE TABLE user (
    id INT NOT NULL AUTO_INCREMENT,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    national_id VARCHAR(20) NOT NULL,
    face_encoding TEXT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_email (email),
    UNIQUE KEY uq_user_national_id (national_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE election (
    id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_election_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE candidate (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    party VARCHAR(100) NOT NULL,
    bio TEXT NULL,
    election_id INT NOT NULL,
    photo VARCHAR(255) NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    KEY idx_candidate_election (election_id),
    CONSTRAINT fk_candidate_election
        FOREIGN KEY (election_id) REFERENCES election (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE vote (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    election_id INT NOT NULL,
    candidate_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    encrypted_vote TEXT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vote_user_election (user_id, election_id),
    KEY idx_vote_election (election_id),
    KEY idx_vote_candidate (candidate_id),
    CONSTRAINT fk_vote_user
        FOREIGN KEY (user_id) REFERENCES user (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_vote_election
        FOREIGN KEY (election_id) REFERENCES election (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_vote_candidate
        FOREIGN KEY (candidate_id) REFERENCES candidate (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Optional admin seed record:
-- INSERT INTO user (email, password_hash, first_name, last_name, national_id, is_admin, is_verified)
-- VALUES ('admin@example.com', '<hashed_password>', 'Admin', 'Admin', 'AB123456', TRUE, TRUE);