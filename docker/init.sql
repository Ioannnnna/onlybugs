CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  country VARCHAR(50),
  balance NUMERIC
);

INSERT INTO customers (name, country, balance) VALUES
('Alice', 'USA', 5000),
('Bob', 'Canada', 3200),
('Charlie', 'UK', 4700),
('Diana', 'Germany', 9100),
('Eva', 'Japan', 2450);
