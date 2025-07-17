CREATE TABLE User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    is_blocked BOOLEAN DEFAULT FALSE,
    balance DECIMAL(10,2) DEFAULT 0 NOT NULL,
    contact_info_address VARCHAR(255),
    contact_info_phone_no VARCHAR(20)
);

ALTER TABLE User
ADD CONSTRAINT chk_balance CHECK (balance >= 0);

ALTER TABLE User ADD COLUMN reset_token VARCHAR(255);
ALTER TABLE User ADD COLUMN token_expiration DATETIME;

CREATE TABLE Seller (
    user_id INT PRIMARY KEY,
    tax_number VARCHAR(255) NOT NULL,
    business_address VARCHAR(255),
    business_name VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    bio TEXT,
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

ALTER TABLE Seller
ADD CONSTRAINT unq_tax_number UNIQUE (tax_number);

DELIMITER $$
CREATE TRIGGER trg_before_insert_seller
BEFORE INSERT ON Seller
FOR EACH ROW
BEGIN
    DECLARE msg VARCHAR(255);
    IF EXISTS (SELECT 1 FROM Buyer WHERE user_id = NEW.user_id) THEN
        SET msg = CONCAT('Error: User with ID ', NEW.user_id, ' already exists as a Buyer.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;
END$$
DELIMITER ;

CREATE TABLE Buyer (
    user_id INT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

DELIMITER $$
CREATE TRIGGER trg_before_insert_buyer
BEFORE INSERT ON Buyer
FOR EACH ROW
BEGIN
    DECLARE msg VARCHAR(255);
    IF EXISTS (SELECT 1 FROM Seller WHERE user_id = NEW.user_id) THEN
        SET msg = CONCAT('Error: User with ID ', NEW.user_id, ' already exists as a Seller.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = msg;
    END IF;
END$$
DELIMITER ;

CREATE TABLE Admin (
    admin_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    surname VARCHAR(255),
    last_login TIMESTAMP
);

CREATE TABLE Product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_price DECIMAL(10, 2) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_stock INT NOT NULL,
    product_type VARCHAR(100),
    product_description TEXT,
    product_gender ENUM('male', 'female', 'unisex adult','unisex kid', 'boy', 'girl', 'unisex') DEFAULT 'unisex adult',
    product_brand VARCHAR(100),
    product_size VARCHAR(50),
    creation_date DATETIME NOT NULL,
    last_update_date DATETIME NOT NULL,
    fav_count INT DEFAULT 0,
    user_id INT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES Seller(user_id)
);

ALTER TABLE Product
ADD CONSTRAINT chk_stock CHECK (product_stock >= 0);

CREATE VIEW ProductDetails AS
SELECT p.product_id, p.product_name,p.is_deleted, p.product_price, p.product_description,p.product_stock, s.business_name, s.is_verified, s.user_id
FROM Product p
JOIN Seller s ON p.user_id = s.user_id;

DELIMITER $$
CREATE TRIGGER trg_update_product
BEFORE UPDATE ON Product
FOR EACH ROW
BEGIN
    SET NEW.last_update_date = NOW();
END$$
DELIMITER ;

CREATE TABLE Image (
    image_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    image_data MEDIUMBLOB NOT NULL,
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

DELIMITER $$
CREATE TRIGGER check_image_count_before_insert
BEFORE INSERT ON Image
FOR EACH ROW
BEGIN
    DECLARE img_count INT;
    SELECT COUNT(*) INTO img_count FROM Image WHERE product_id = NEW.product_id;
    IF img_count >= 5 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot add more than 5 images per product.';
    END IF;
END$$
DELIMITER ;

CREATE TABLE `Order` (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_status ENUM('SELECTED', 'PAYMENT', 'ORDERED', 'SHIPPED', 'FINALIZED', 'RETURNED', 'RETURN_FINALIZED','RETURN_REJECTED', 'REJECTED') NOT NULL,
    order_amount INT NOT NULL,
    order_date DATE,
    order_address VARCHAR(255) NOT NULL,
    payment_method ENUM('BALANCE','CARD'),
    card_number VARCHAR(255),
    arrival_date DATE,
    shipping_date DATE,
    finalized_date DATE,
    return_date DATE,
    return_finalized_date DATE,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

CREATE INDEX idx_order_user ON `Order` (user_id);
CREATE INDEX idx_order_product ON `Order` (product_id);
CREATE INDEX idx_order_status ON `Order` (order_status);



CREATE TABLE Review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    review_content TEXT,
    star_count INT CHECK (star_count BETWEEN 1 AND 5),
    post_date DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

CREATE VIEW ReviewDetails AS
SELECT r.review_id, r.star_count, r.review_content, r.post_date, u.username, u.name
FROM Review r
JOIN User u ON r.user_id = u.user_id;

CREATE TABLE Favorites (
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    favorite_date DATETIME NOT NULL,
    PRIMARY KEY (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

CREATE TABLE Report (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    reporting_user_id INT NOT NULL,
    report_date DATETIME NOT NULL,
    description TEXT,
    FOREIGN KEY (reporting_user_id) REFERENCES User(user_id)
);

CREATE TABLE User_Report (
    report_id INT PRIMARY KEY,
    reported_user_id INT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES Report(report_id),
    FOREIGN KEY (reported_user_id) REFERENCES User(user_id)
);

CREATE TABLE Product_Report (
    report_id INT PRIMARY KEY,
    reported_product_id INT NOT NULL,
    report_reason ENUM('inappropriate', 'false_information', 'spam', 'other') NOT NULL,
    FOREIGN KEY (report_id) REFERENCES Report(report_id),
    FOREIGN KEY (reported_product_id) REFERENCES Product(product_id)
);

CREATE TABLE SystemReport (
    system_report_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    report_name VARCHAR(255) NOT NULL,
    report_date DATETIME NOT NULL,
    report_details TEXT,
    report_file BLOB,
    FOREIGN KEY (admin_id) REFERENCES Admin(admin_id)
);

-- Inserting into User table
-- Inserting into User table
INSERT INTO User (username, name, surname, email, password, is_blocked, balance, contact_info_address, contact_info_phone_no)
VALUES ('john_doe', 'John', 'Doe', 'john.doe@example.com', '123456', FALSE, 100.00, '123 Main St', '123-456-7890'),
       ('jane_smith', 'Jane', 'Smith', 'jane.smith@example.com', '123456', FALSE, 150.00, '456 Elm St', '234-567-8901'),
       ('bob_johnson', 'Bob', 'Johnson', 'bob.johnson@example.com', '123456', FALSE, 200.00, '789 Oak St', '345-678-9012'),
       ('alice_brown', 'Alice', 'Brown', 'alice.brown@example.com', '123456', FALSE, 50.00, '101 Pine St', '456-789-0123'),
       ('charlie_davis', 'Charlie', 'Davis', 'charlie.davis@example.com', '123456', FALSE, 120.00, '202 Birch St', '567-890-1234'),
       ('diana_white', 'Diana', 'White', 'diana.white@example.com', '123456', FALSE, 180.00, '303 Cedar St', '678-901-2345'),
       ('edward_black', 'Edward', 'Black', 'edward.black@example.com', '123456', FALSE, 90.00, '404 Maple St', '789-012-3456'),
       ('fiona_green', 'Fiona', 'Green', 'fiona.green@example.com', '123456', FALSE, 160.00, '505 Walnut St', '890-123-4567');

-- Inserting into Seller table
INSERT INTO Seller (user_id, tax_number, business_address, business_name, is_verified, bio)
VALUES (3, '123456789', '789 Oak St', 'Bob\'s Crafts', TRUE, 'We sell handmade crafts.'),
       (4, '987654321', '101 Pine St', 'Alice\'s Arts', TRUE, 'Unique handcrafted art pieces.'),
       (7, '456123789', '404 Maple St', 'Black\'s Boutique', TRUE, 'Exclusive clothing and accessories.'),
       (8, '789654123', '505 Walnut St', 'Green\'s Garden', TRUE, 'Organic fruits and vegetables.');

-- Inserting into Buyer table
INSERT INTO Buyer (user_id)
VALUES (1),
       (2),
       (5),
       (6);


INSERT INTO Admin (username, email, password, name, surname, last_login)
VALUES ('admin1', 'admin@example.com', 'hashed_admin_password', 'Admin', 'One', '2023-01-01 12:00:00');

INSERT INTO Product (product_id, product_price, product_name, product_stock, product_type, product_description, product_gender, product_brand, product_size, creation_date, last_update_date, fav_count, user_id, is_deleted)
VALUES
(1, 25.00, 'bu silindiii', 10, 'Ceramics', 'Beautiful handmade vase', 'unisex adult', 'CraftsBrand', 'Medium', '2023-01-10 12:15:00', '2023-01-10 12:15:00', 5, 3, TRUE),
(2, 25.00, 'bu silinmedi', 10, 'Ceramics', 'Beautiful handmade vase', 'unisex adult', 'CraftsBrand', 'Medium', '2023-01-10 12:10:00', '2023-01-10 12:10:00', 5, 3, FALSE),
(3, 25.00, 'Handmade Vase', 10, 'Ceramics', 'Beautiful handmade vase', 'unisex adult', 'CraftsBrand', 'Medium', '2023-01-10 12:00:00', '2023-01-10 12:00:00', 5, 3, FALSE),
(4, 50.00, 'Wooden Sculpture', 5, 'Woodwork', 'Intricate wooden sculpture', 'unisex adult', 'ArtBrand', 'Large', '2023-01-15 12:00:00', '2023-01-15 12:00:00', 2, 4, FALSE),
(5, 30.00, 'Handmade Mug', 15, 'Ceramics', 'Handmade ceramic mug', 'unisex', 'CraftsBrand', 'Small', '2023-01-20 12:00:00', '2023-01-20 12:00:00', 3, 3, FALSE),
(6, 75.00, 'Wooden Table', 3, 'Woodwork', 'Handcrafted wooden table', 'unisex', 'FurnitureBrand', 'Large', '2023-02-10 12:00:00', '2023-02-10 12:00:00', 1, 4, FALSE),
(7, 45.00, 'Knitted Scarf', 20, 'Textiles', 'Warm knitted scarf', 'unisex', 'TextileBrand', 'Medium', '2023-02-15 12:00:00', '2023-02-15 12:00:00', 4, 7, FALSE),
(8, 100.00, 'Leather Wallet', 8, 'Leatherwork', 'Premium leather wallet', 'male', 'LeatherBrand', 'Small', '2023-03-01 12:00:00', '2023-03-01 12:00:00', 7, 4, FALSE),
(9, 60.00, 'Glass Vase', 12, 'Glasswork', 'Handblown glass vase', 'unisex', 'GlassBrand', 'Medium', '2023-03-05 12:00:00', '2023-03-05 12:00:00', 5, 3, FALSE),
(10, 20.00, 'Handmade Notebook', 25, 'Paperwork', 'Handmade paper notebook', 'unisex', 'PaperBrand', 'Medium', '2023-03-10 12:00:00', '2023-03-10 12:00:00', 6, 8, FALSE),
(11, 85.00, 'Knitted Blanket', 7, 'Textiles', 'Warm knitted blanket', 'unisex', 'TextileBrand', 'Large', '2023-03-20 12:00:00', '2023-03-20 12:00:00', 2, 7, FALSE),
(12, 40.00, 'Ceramic Plate Set', 10, 'Ceramics', 'Set of 4 handmade ceramic plates', 'unisex', 'CraftsBrand', 'Medium', '2023-03-25 12:00:00', '2023-03-25 12:00:00', 8, 3, FALSE),
(13, 55.00, 'Wooden Chair', 6, 'Woodwork', 'Handcrafted wooden chair', 'unisex', 'FurnitureBrand', 'Large', '2023-04-01 12:00:00', '2023-04-01 12:00:00', 3, 4, FALSE),
(14, 15.00, 'Handmade Soap', 30, 'Cosmetics', 'Natural handmade soap', 'unisex', 'SoapBrand', 'Small', '2023-04-05 12:00:00', '2023-04-05 12:00:00', 9, 8, FALSE),
(15, 100.00, 'Custom Necklace', 5, 'Jewelry', 'Custom handmade necklace', 'female', 'JewelryBrand', 'Small', '2023-04-10 12:00:00', '2023-04-10 12:00:00', 6, 4, FALSE);

INSERT INTO `Order` (order_status, order_amount, order_date, order_address, payment_method, card_number, arrival_date, shipping_date, finalized_date, return_date, return_finalized_date, user_id, product_id)
VALUES
    ('ORDERED', 30, '2024-04-10', '123 Main St', 'BALANCE', NULL, NULL, NULL, NULL, NULL, NULL, 1, 3),
    ('SHIPPED', 75, '2024-04-12', '456 Elm St', 'BALANCE', NULL, NULL, '2024-04-13', NULL, NULL, NULL, 2, 4),
    ('FINALIZED', 45, '2024-04-14', '789 Oak St', 'BALANCE', NULL, '2024-04-19', '2024-04-15', '2024-04-20', NULL, NULL, 1, 5),
    ('RETURNED', 100, '2024-03-05', '321 Pine St', 'BALANCE', NULL, '2024-03-10', '2024-03-06', '2024-03-11', '2024-03-09', NULL, 2, 6),
    ('ORDERED', 60, '2024-03-15', '654 Maple St', 'BALANCE', NULL, '2024-03-20', NULL, NULL, NULL, NULL, 1, 7),
    ('SHIPPED', 20, '2024-03-17', '987 Birch St', 'BALANCE', NULL, '2024-03-22', NULL, '2024-03-23', NULL, NULL, 2, 8),
    ('FINALIZED', 85, '2024-03-25', '159 Cedar St', 'BALANCE', NULL, '2024-03-30', '2024-03-26', '2024-03-31', NULL, NULL, 1, 9),
    ('RETURNED', 40, '2024-04-01', '753 Spruce St', 'BALANCE', NULL, '2024-04-06', '2024-04-02', '2024-04-07', '2024-04-05', NULL, 2, 10),
    ('ORDERED', 55, '2024-04-05', '852 Willow St', 'BALANCE', NULL, NULL, NULL, NULL, NULL, NULL, 1, 11),
    ('SHIPPED', 15, '2024-04-08', '963 Redwood St', 'BALANCE', NULL, NULL, '2024-04-09', NULL, NULL, NULL, 2, 12),
    ('FINALIZED', 30, '2023-11-30', '321 Pine St', 'BALANCE', NULL, '2023-12-05', '2023-12-01', '2023-12-06', NULL, NULL, 5, 13),
    ('FINALIZED', 25, '2023-12-15', '456 Elm St', 'BALANCE', NULL, '2023-12-20', '2023-12-16', '2023-12-21', NULL, NULL, 6, 14),
    ('FINALIZED', 50, '2024-01-05', '789 Oak St', 'BALANCE', NULL, '2024-01-10', '2024-01-06', '2024-01-11', NULL, NULL, 1, 15),
    ('FINALIZED', 75, '2024-01-20', '987 Birch St', 'BALANCE', NULL, '2024-01-25', '2024-01-21', '2024-01-26', NULL, NULL, 2, 1),
    ('FINALIZED', 35, '2024-02-10', '852 Willow St', 'BALANCE', NULL, '2024-02-15', '2024-02-11', '2024-02-16', NULL, NULL, 5, 2),
    ('FINALIZED', 40, '2024-02-25', '963 Redwood St', 'BALANCE', NULL, '2024-03-02', '2024-02-26', '2024-03-03', NULL, NULL, 6, 3),
    ('FINALIZED', 60, '2024-03-10', '123 Main St', 'BALANCE', NULL, '2024-03-15', '2024-03-11', '2024-03-16', NULL, NULL, 1, 4),
    ('FINALIZED', 80, '2024-03-20', '456 Elm St', 'BALANCE', NULL, '2024-03-25', '2024-03-21', '2024-03-26', NULL, NULL, 2, 5),
    ('FINALIZED', 55, '2024-04-01', '789 Oak St', 'BALANCE', NULL, '2024-04-06', '2024-04-02', '2024-04-07', NULL, NULL, 5, 6),
    ('FINALIZED', 65, '2024-04-10', '987 Birch St', 'BALANCE', NULL, '2024-04-15', '2024-04-11', '2024-04-16', NULL, NULL, 6, 7);

-- Inserting additional sells records


-- Inserting additional reviews
INSERT INTO Review (user_id, product_id, review_content, star_count, post_date)
VALUES (1, 3, 'Nice mug, very well made.', 5, '2023-01-31 13:00:00'),
       (2, 4, 'The table is sturdy and beautiful.', 4, '2023-02-13 13:00:00'),
       (1, 5, 'Love the scarf, very warm.', 5, '2023-02-21 13:00:00'),
       (2, 6, 'High quality wallet.', 4, '2023-03-06 13:00:00'),
       (1, 7, 'The vase is a perfect addition to my decor.', 5, '2023-03-13 13:00:00'),
       (2, 8, 'Great notebook for daily use.', 4, '2023-03-16 13:00:00'),
       (1, 9, 'The blanket is very cozy.', 5, '2023-03-26 13:00:00'),
       (2, 10, 'Beautiful plates, love the design.', 4, '2023-04-02 13:00:00'),
       (1, 11, 'The chair is comfortable and well-made.', 5, '2023-04-06 13:00:00'),
       (2, 12, 'The soap smells amazing.', 4, '2023-04-11 13:00:00');

-- Inserting additional favorites
INSERT INTO Favorites (user_id, product_id, favorite_date)
VALUES (1, 3, '2023-01-30 12:00:00'),
       (2, 4, '2023-02-12 12:00:00'),
       (1, 5, '2023-02-20 12:00:00'),
       (2, 6, '2023-03-05 12:00:00'),
       (1, 7, '2023-03-12 12:00:00'),
       (2, 8, '2023-03-15 12:00:00'),
       (1, 9, '2023-03-25 12:00:00'),
       (2, 10, '2023-04-01 12:00:00'),
       (1, 11, '2023-04-05 12:00:00'),
       (2, 12, '2023-04-10 12:00:00');

-- Inserting mock reports for users
-- Inserting into Report table for user reports
INSERT INTO Report (reporting_user_id, report_date, description)
VALUES
(1, '2023-05-01 08:00:00', 'User has been posting inappropriate content.'),
(2, '2023-05-02 10:00:00', 'User is engaging in spammy behavior.'),
(5, '2023-06-10 09:00:00', 'User is creating multiple accounts.'),
(6, '2023-07-15 11:00:00', 'User is using offensive language.'),
(1, '2023-08-20 14:00:00', 'User is harassing other users.');

-- Inserting into Report table for product reports
INSERT INTO Report (reporting_user_id, report_date, description)
VALUES
(1, '2023-05-03 12:00:00', 'Product contains false information.'),
(2, '2023-05-04 14:00:00', 'Product images do not match the description.'),
(5, '2024-01-12 16:00:00', 'Product is counterfeit.'),
(6, '2024-02-14 18:00:00', 'Product description is misleading.'),
(1, '2024-03-18 20:00:00', 'Product received is damaged.');

-- Inserting into User_Report table
INSERT INTO User_Report (report_id, reported_user_id)
VALUES
(1, 2), -- Report ID 1 for user with ID 3
(2, 4), -- Report ID 2 for user with ID 4
(3, 2), -- Report ID 3 for user with ID 7
(4, 8), -- Report ID 4 for user with ID 8
(5, 3); -- Report ID 5 for user with ID 3

-- Inserting into Product_Report table
INSERT INTO Product_Report (report_id, reported_product_id, report_reason)
VALUES
(6, 1, 'false_information'), -- Report ID 6 for product with ID 1
(7, 2, 'inappropriate'), -- Report ID 7 for product with ID 2
(8, 3, 'false_information'), -- Report ID 8 for product with ID 3
(9, 4, 'spam'), -- Report ID 9 for product with ID 4
(10, 5, 'other'); -- Report ID 10 for product with ID 5


DELIMITER $$

CREATE PROCEDURE check_and_update_order(
    IN p_order_id INT,
    IN p_user_id INT,
    IN p_quantity DECIMAL(10, 2),
    IN p_payment_method VARCHAR(50),
    IN p_card_number VARCHAR(50),
    IN p_address VARCHAR(255)
)
BEGIN
    DECLARE v_product_id INT;
    DECLARE v_stock DECIMAL(10, 2);
    DECLARE v_total_ordered DECIMAL(10, 2);
    DECLARE v_message VARCHAR(255);
    DECLARE v_status VARCHAR(10) DEFAULT 'success';

    -- Get the product ID and stock for the order
    SELECT p.product_id, p.product_stock INTO v_product_id, v_stock
    FROM `Order` o
    JOIN `Product` p ON o.product_id = p.product_id
    WHERE o.order_id = p_order_id AND o.user_id = p_user_id;

    -- Calculate the total ordered quantity for the product excluding the current order
    SELECT IFNULL(SUM(order_amount), 0) INTO v_total_ordered
    FROM `Order`
    WHERE user_id = p_user_id AND product_id = v_product_id AND order_id != p_order_id;

    -- Check if the total ordered quantity exceeds the stock
    IF v_total_ordered + p_quantity > v_stock THEN
        SET v_status = 'error';
        SET v_message = CONCAT('Cannot update cart: Total quantity for product ', v_product_id, ' exceeds available stock.');
    ELSE
        -- Update the order
        UPDATE `Order`
        SET order_amount = p_quantity, payment_method = p_payment_method, card_number = p_card_number, order_address = p_address
        WHERE order_id = p_order_id AND user_id = p_user_id;
    END IF;

    -- Return the result
    SELECT v_status AS status, v_message AS message;
END$$

DELIMITER ;

DELIMITER ;

 DELIMITER $$

CREATE PROCEDURE commit_all_orders(
    IN p_user_id INT
)
BEGIN
    DECLARE v_order_id INT;
    DECLARE v_product_id INT;
    DECLARE v_stock DECIMAL(10, 2);
    DECLARE v_order_amount INT;
    DECLARE v_user_balance DECIMAL(10, 2);
    DECLARE v_payment_method VARCHAR(50);
    DECLARE v_card_number VARCHAR(50);
    DECLARE v_total_price DECIMAL(10, 2);
    DECLARE v_product_price DECIMAL(10, 2);
    DECLARE v_message VARCHAR(255);
    DECLARE v_status VARCHAR(10) DEFAULT 'success';
    DECLARE done INT DEFAULT 0;

    -- Declare a cursor to iterate over the orders
    DECLARE order_cursor CURSOR FOR
        SELECT order_id, product_id, order_amount, payment_method, card_number
        FROM `Order`
        WHERE user_id = p_user_id AND order_status = 'SELECTED';

    -- Declare a handler to close the cursor
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    -- Open the cursor
    OPEN order_cursor;

    -- Iterate over the orders
    read_loop: LOOP
        FETCH order_cursor INTO v_order_id, v_product_id, v_order_amount, v_payment_method, v_card_number;

        IF done THEN
            LEAVE read_loop;
        END IF;

        -- Get the product stock and price
        SELECT product_stock, product_price INTO v_stock, v_product_price
        FROM `Product`
        WHERE product_id = v_product_id;

        -- Calculate the total price
        SET v_total_price = v_order_amount * v_product_price;

        -- Check if the total ordered quantity exceeds the stock
        IF v_order_amount > v_stock THEN
            SET v_status = 'error';
            SET v_message = CONCAT('Cannot commit order: Total quantity for product ', v_product_id, ' exceeds available stock.');
            LEAVE read_loop;
        ELSEIF v_payment_method = 'BALANCE' THEN
            -- Check if the user has enough balance
            SELECT balance INTO v_user_balance
            FROM `User`
            WHERE user_id = p_user_id;

            IF v_user_balance < v_total_price THEN
                SET v_status = 'error';
                SET v_message = 'Cannot commit order: Insufficient balance.';
                LEAVE read_loop;
            ELSE
                -- Update user balance
                UPDATE `User`
                SET balance = balance - v_total_price
                WHERE user_id = p_user_id;

                -- Check if the balance update was successful
                IF ROW_COUNT() = 0 THEN
                    SET v_status = 'error';
                    SET v_message = 'Failed to update user balance.';
                    LEAVE read_loop;
                END IF;
            END IF;
        END IF;

        -- Update the order status and details
        UPDATE `Order`
        SET order_status = 'ORDERED'
        WHERE order_id = v_order_id;

    END LOOP;

    -- Close the cursor
    CLOSE order_cursor;

    -- Return the result
    SELECT v_status AS status, v_message AS message;
END$$

DELIMITER ;