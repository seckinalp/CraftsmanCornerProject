# CraftsmanCorner Project

A comprehensive e-commerce web application built with Flask that connects craftspeople and artisans with customers looking for unique, handmade products. CraftsmanCorner provides a marketplace where sellers can showcase their handcrafted items and buyers can discover and purchase authentic artisanal goods.

## 🌟 Features

### For Buyers
- **Product Discovery**: Browse and search through a curated collection of handcrafted items
- **Advanced Filtering**: Filter products by type, gender, brand, size, price range, and seller
- **Shopping Cart**: Add products to cart and manage quantities
- **Order Management**: Track order history and status
- **Favorites**: Save favorite products for later
- **User Balance**: Manage account balance for purchases
- **Shop Directory**: Browse all registered shops and sellers
- **Review System**: Rate and review purchased products
- **Reporting**: Report inappropriate content or issues

### For Sellers
- **Product Management**: Add, edit, and manage product listings with multiple images
- **Inventory Tracking**: Monitor stock levels and product performance
- **Order Processing**: View and manage incoming orders
- **Business Profile**: Create detailed seller profiles with business information
- **Sales Analytics**: Access sales reports and performance metrics
- **Balance Management**: Withdraw earnings from sales
- **Verification System**: Get verified seller status for increased credibility

### For Administrators
- **User Management**: Oversee buyer and seller accounts
- **Content Moderation**: Review and respond to user reports
- **System Analytics**: Generate comprehensive system reports
- **Platform Oversight**: Monitor platform health and user activity

## 🏗️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL 5.7
- **Frontend**: HTML5, CSS3, Bootstrap 4, JavaScript
- **Email Service**: Flask-Mail with SMTP
- **File Upload**: Werkzeug secure file handling
- **Containerization**: Docker & Docker Compose
- **Session Management**: Flask sessions
- **Security**: Password hashing, SQL injection protection

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- MySQL 5.7+ (for local development)

## 🚀 Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CraftsmanCornerProject
   ```

2. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - The MySQL database will be available on `localhost:3307`

The application will automatically:
- Set up the MySQL database
- Create all necessary tables using `schema.sql`
- Insert sample data
- Start the Flask application

## 🛠️ Local Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up MySQL database**
   ```bash
   mysql -u root -p
   CREATE DATABASE craftsmancornerdb;
   ```

3. **Import database schema**
   ```bash
   mysql -u root -p craftsmancornerdb < schema.sql
   ```

4. **Configure environment**
   Update the database configuration in `app/app.py`:
   ```python
   app.config['MYSQL_HOST'] = 'localhost'  # Change from 'db' to 'localhost'
   app.config['MYSQL_USER'] = 'root'
   app.config['MYSQL_PASSWORD'] = 'your_password'
   app.config['MYSQL_DB'] = 'craftsmancornerdb'
   ```

5. **Run the application**
   ```bash
   cd app
   python app.py
   ```

## 📁 Project Structure

```
CraftsmanCornerProject/
├── app/
│   ├── admin/              # Admin functionality
│   │   ├── __init__.py
│   │   └── route.py        # Admin routes and dashboard
│   ├── static/             # Static assets
│   │   ├── logo.png        # Application logos
│   │   └── products/       # Product images
│   ├── templates/          # HTML templates
│   │   ├── admin/          # Admin templates
│   │   ├── buyer_*.html    # Buyer interface templates
│   │   ├── seller_*.html   # Seller interface templates
│   │   └── *.html          # General templates
│   ├── app.py              # Main Flask application
│   ├── product.py          # Product management blueprint
│   ├── profile.py          # User profile management
│   ├── order.py            # Order processing
│   └── report.py           # Reporting system
├── docker-compose.yaml     # Docker composition configuration
├── Dockerfile              # Docker container configuration
├── requirements.txt        # Python dependencies
├── schema.sql             # Database schema and sample data
└── README.md              # Project documentation
```

## 🎯 Getting Started

### First Time Setup

1. **Start the application** using Docker or local setup
2. **Create accounts**:
   - Visit `http://localhost:5000`
   - Register as a buyer or seller
   - Admin login is available at `/admin/login_admin`

### Sample User Types

- **Buyers**: Can browse, search, and purchase products
- **Sellers**: Can list products, manage inventory, and process orders
- **Admins**: Have full system access for moderation and analytics

## 🔧 Configuration

### Email Configuration
Update email settings in `app/app.py`:
```python
app.config['MAIL_SERVER'] = 'your-smtp-server.com'
app.config['MAIL_USERNAME'] = 'your-email@domain.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'
```

### File Upload Configuration
```python
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
```

## 📊 Database Schema

The application uses a comprehensive database schema with the following main entities:

- **User**: Base user information with balance management
- **Buyer/Seller**: Role-specific user extensions
- **Product**: Product catalog with images and metadata
- **Order**: Order processing and tracking
- **Review**: Product reviews and ratings
- **Report**: User reporting system
- **Admin**: Administrative users

## 🔐 Security Features

- Password hashing for user accounts
- SQL injection protection through parameterized queries
- Secure file upload handling
- Session-based authentication
- Role-based access control
- User blocking/banning capabilities

## 🌐 API Endpoints

### Main Routes
- `/` - Home page
- `/login` - User authentication
- `/register_buyer` - Buyer registration
- `/register_seller` - Seller registration
- `/buyer_dashboard` - Buyer interface
- `/seller_dashboard` - Seller interface

### Module Routes
- `/product/*` - Product management
- `/order/*` - Order processing
- `/report/*` - Reporting system
- `/admin/*` - Administrative functions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Support

For support, please create an issue in the repository or contact the development team.

## 🚀 Future Enhancements

- Payment gateway integration
- Real-time chat between buyers and sellers
- Mobile application
- Advanced analytics dashboard
- Multi-language support
- Social media integration
- API for third-party integrations

