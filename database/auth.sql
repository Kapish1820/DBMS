CREATE DATABASE stock_management_system;
USE stock_management_system;

CREATE TABLE User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    age INT GENERATED ALWAYS AS (YEAR(CURDATE()) - YEAR(date_of_birth)) STORED,
    mail_id VARCHAR(100) UNIQUE NOT NULL,
    pan_id VARCHAR(10) UNIQUE NOT NULL
);
