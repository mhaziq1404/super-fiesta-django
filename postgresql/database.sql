CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user VARCHAR NOT NULL,
    nickname VARCHAR,
    score INT, 
    games_played INT, 
    games_won INT, 
    created_at DATE, 
    updated_at DATE
);