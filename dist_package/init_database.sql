-- Database initialization script for Hostel Registration System
-- Run this as MySQL root user to set up both databases

-- Create source database (umatdb) - used by scraper
CREATE DATABASE IF NOT EXISTS `umatdb` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create registration database (hostel_db) - used by registration app
CREATE DATABASE IF NOT EXISTS `hostel_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create registered_students table in hostel_db
USE `hostel_db`;

CREATE TABLE IF NOT EXISTS `registered_students` (
    `id` VARCHAR(255) PRIMARY KEY,
    `formReferenceNo` VARCHAR(255),
    `fullName` VARCHAR(255),
    `email` VARCHAR(255),
    `programme` VARCHAR(255),
    `phoneNumber` VARCHAR(50),
    `hostel` VARCHAR(255),
    `souvenirs_paid` BOOLEAN DEFAULT FALSE,
    `registeredAt` DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create indexes for better search performance
CREATE INDEX idx_fullName ON `registered_students`(`fullName`);
CREATE INDEX idx_formReferenceNo ON `registered_students`(`formReferenceNo`);
CREATE INDEX idx_programme ON `registered_students`(`programme`);
CREATE INDEX idx_phoneNumber ON `registered_students`(`phoneNumber`);

-- Show created databases and tables
SHOW DATABASES LIKE 'umatdb';
SHOW DATABASES LIKE 'hostel_db';
USE `hostel_db`;
SHOW TABLES;
DESCRIBE `registered_students`;