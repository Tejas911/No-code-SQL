CREATE DATABASE high_school;
USE high_school;

CREATE TABLE students (
    roll_number INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    standard ENUM('9', '10') NOT NULL,
    english INT NOT NULL,
    math INT NOT NULL,
    chemistry INT NOT NULL,
    physics INT NOT NULL,
    history INT NOT NULL
);

INSERT INTO students (roll_number, name, standard, english, math, chemistry, physics, history)
VALUES
(1, 'John Doe', '9', 78, 85, 76, 89, 90),
(2, 'Jane Smith', '9', 88, 92, 91, 87, 76),
(3, 'Samuel Johnson', '10', 75, 80, 83, 79, 88),
(4, 'Emma Watson', '10', 91, 96, 89, 85, 82),
(5, 'David Lee', '9', 67, 74, 81, 78, 85),
(6, 'Sophia Williams', '10', 93, 89, 78, 84, 90),
(7, 'James Brown', '9', 81, 72, 84, 79, 77),
(8, 'Olivia Miller', '9', 85, 83, 82, 91, 89),
(9, 'Michael Davis', '10', 79, 88, 87, 92, 85),
(10, 'Isabella Garcia', '10', 90, 94, 85, 81, 79),
(11, 'Ethan Martinez', '9', 65, 75, 79, 83, 91),
(12, 'Ava Rodriguez', '9', 82, 86, 81, 88, 84),
(13, 'Alexander Hernandez', '10', 87, 92, 89, 83, 75),
(14, 'Charlotte Wilson', '9', 90, 85, 84, 87, 79),
(15, 'Daniel Moore', '10', 88, 80, 77, 90, 84),
(16, 'Amelia Taylor', '9', 79, 87, 91, 84, 88),
(17, 'Lucas Anderson', '10', 91, 93, 88, 89, 77),
(18, 'Mia Thomas', '9', 84, 79, 75, 82, 87),
(19, 'Elijah Jackson', '10', 76, 85, 84, 90, 91),
(20, 'Harper White', '9', 92, 81, 89, 85, 83),
(21, 'Mason Harris', '10', 88, 82, 80, 77, 90),
(22, 'Sofia Clark', '9', 89, 94, 92, 78, 87),
(23, 'Logan Lewis', '10', 85, 87, 79, 83, 88),
(24, 'Ella Lee', '9', 83, 82, 81, 90, 89),
(25, 'Jackson Walker', '10', 91, 84, 88, 87, 76),
(26, 'Grace Hall', '9', 90, 92, 86, 84, 79),
(27, 'Benjamin Young', '10', 79, 86, 89, 91, 84),
(28, 'Chloe King', '9', 84, 79, 87, 83, 85),
(29, 'Aiden Wright', '10', 82, 88, 85, 79, 92),
(30, 'Lily Scott', '9', 91, 94, 90, 88, 86);
