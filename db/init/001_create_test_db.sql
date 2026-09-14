-- Runs once, on first container creation, via Postgres's docker-entrypoint-initdb.d
-- mechanism. Gives the backend test suite a database to run against on
-- localhost:5432 without any extra setup steps.
CREATE DATABASE lenny_growth_assistant_test;
