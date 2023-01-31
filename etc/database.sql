CREATE TABLE messages (
    id BIGINT PRIMARY KEY,
    type SMALLINT NOT NULL,
    status SMALLINT NOT NULL,
    author_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    content TEXT
);

CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username varchar(32) NOT NULL,
    discriminator SMALLINT NOT NULL,
    avatar varchar(32),
    bot BOOLEAN DEFAULT false NOT NULL,
    public_flags SMALLINT NOT NULL
);
    
