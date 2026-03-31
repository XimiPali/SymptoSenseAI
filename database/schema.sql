-- ============================================================
-- Healthcare AI Assistant - MySQL Database Schema
-- v2: gender + age on users; structured symptom + demographic
--     context stored with every prediction
-- ============================================================

CREATE DATABASE IF NOT EXISTS healthcare_ai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE healthcare_ai;

-- ============================================================
-- USERS TABLE
-- gender : ENUM('male','female') – required at registration
-- age    : INT 0-120             – required at registration
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)           NOT NULL UNIQUE,
    email       VARCHAR(120)          NOT NULL UNIQUE,
    password    VARCHAR(255)          NOT NULL,
    gender      ENUM('male','female') NOT NULL,
    age         INT                   NOT NULL CHECK (age BETWEEN 0 AND 120),
    is_active   BOOLEAN               NOT NULL DEFAULT TRUE,
    created_at  DATETIME              NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME              NOT NULL DEFAULT CURRENT_TIMESTAMP
                                      ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================================
-- DISEASES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS diseases (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SYMPTOMS TABLE
-- weight : severity score 1-7 from Symptom-severity.csv
-- ============================================================
CREATE TABLE IF NOT EXISTS symptoms (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    weight      INT          NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- DISEASE_SYMPTOMS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS disease_symptoms (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disease_id  INT NOT NULL,
    symptom_id  INT NOT NULL,
    FOREIGN KEY (disease_id) REFERENCES diseases(id) ON DELETE CASCADE,
    FOREIGN KEY (symptom_id) REFERENCES symptoms(id) ON DELETE CASCADE,
    UNIQUE KEY uq_disease_symptom (disease_id, symptom_id)
);

-- ============================================================
-- PRECAUTIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS precautions (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    disease_id       INT          NOT NULL,
    precaution_order TINYINT      NOT NULL,
    precaution_text  VARCHAR(255) NOT NULL,
    FOREIGN KEY (disease_id) REFERENCES diseases(id) ON DELETE CASCADE
);

-- ============================================================
-- PREDICTIONS TABLE
-- symptoms_input        : JSON array of {name, duration} objects
-- age_at_prediction     : patient age used for this prediction
-- gender_at_prediction  : patient gender used for this prediction
-- ============================================================
CREATE TABLE IF NOT EXISTS predictions (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    user_id              INT             NOT NULL,
    symptoms_input       TEXT            NOT NULL,
    age_at_prediction    INT,
    gender_at_prediction VARCHAR(10),
    predicted_disease    VARCHAR(100)    NOT NULL,
    confidence           FLOAT           NOT NULL,
    created_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_predictions_user    ON predictions(user_id);
CREATE INDEX idx_disease_symptoms_d  ON disease_symptoms(disease_id);
CREATE INDEX idx_disease_symptoms_s  ON disease_symptoms(symptom_id);
CREATE INDEX idx_precautions_disease ON precautions(disease_id);


-- ============================================================
-- MIGRATION STATEMENTS
-- Run these if upgrading an existing v1 database.
-- Safe to skip on a fresh install.
-- ============================================================

-- ALTER TABLE users
--     ADD COLUMN gender ENUM('male','female') NOT NULL DEFAULT 'male'  AFTER password,
--     ADD COLUMN age    INT                   NOT NULL DEFAULT 25       AFTER gender;

-- ALTER TABLE predictions
--     ADD COLUMN age_at_prediction    INT        AFTER symptoms_input,
--     ADD COLUMN gender_at_prediction VARCHAR(10) AFTER age_at_prediction;
